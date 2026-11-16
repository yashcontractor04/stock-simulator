# Plugins

A plugin is one Python file behind a small fixed interface. The core calls the interface
and never knows which plugin is behind it. Adding something new means writing one file and
registering it. No core file changes.

There are five kinds:

| Kind | Answers the question | v1 plugins | Later |
|---|---|---|---|
| Data provider | Where do prices and company numbers come from? | `tiingo`, `edgar`, `csv` (files, for tests and the bulk load) | `stooq`, `yfinance` (fallback), `trading212` |
| Universe | Which instruments may be picked? | `us-large`, `core-etfs`, `sic-industry`, `theme-list` | `europe` |
| Picker | Which of them pass, and in what order? | `quality-filter`, `low-volatility-rank`, `momentum-rank` | `news-sentiment` |
| Weighting | How much money in each? | `equal-weight`, `inverse-volatility`, `minimum-variance` | `risk-parity` |
| Risk metric | What numbers describe the result? | `volatility`, `max-drawdown`, `var-es`, `sharpe` | `sortino`, `beta` |

## 1. How it works

I use Python **Protocols** (a Protocol describes which methods a class must have; a class
fits if it has them, without inheriting from anything). I chose them over abstract base
classes because a plugin then needs no import from the core except the data types, and the
type checker still catches a wrong signature.

Each kind has a registry: a dictionary from a name to a class, filled by a decorator.

```python
# sim/plugins/registry.py  (sketch)
WEIGHTING: dict[str, type[WeightingStrategy]] = {}

def weighting(name: str):
    def add(cls):
        WEIGHTING[name] = cls
        return cls
    return add
```

All plugin modules are imported once at start-up, in `sim/plugins/__init__.py`. So adding a
plugin is exactly two steps:

1. Write `sim/plugins/weighting/my_strategy.py` with the decorator on top of the class.
2. Add one import line to `sim/plugins/__init__.py`.

Then `"strategy": "my-strategy"` works in the API, and the name shows up in
`GET /v1/meta/options`.

I deliberately do not scan folders or use Python "entry points" to find plugins
automatically. One explicit import line is easier to understand and to debug, and I can see
the full list in one file.

## 2. Shared data types

Small frozen dataclasses that plugins give and take. No plugin ever sees a database
connection or an HTTP client it did not create itself.

```python
@dataclass(frozen=True)
class PriceBar:
    ticker: str
    day: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None

@dataclass(frozen=True)
class CorporateAction:
    ticker: str
    ex_date: date
    kind: Literal["split", "dividend"]
    value: float

@dataclass(frozen=True)
class Fact:               # one company number
    ticker: str
    concept: str
    period_end: date
    filed_at: date        # the day it became public
    value: float
    form: str
```

And one important class, the **market view**: read access to prices and facts that is cut
off at a date.

```python
class MarketView(Protocol):
    as_of: date
    def returns(self, tickers: list[str], lookback_days: int) -> pd.DataFrame: ...
    def latest_fact(self, ticker: str, concept: str) -> float | None: ...
    def members(self, universe: str) -> list[str]: ...
```

Pickers and weighting strategies get a `MarketView`, never the database. The view only
answers with data from on or before `as_of`. This is how look-ahead bias is made
impossible by design instead of by discipline: a plugin cannot peek, because the object it
holds has no future in it.

## 3. The five interfaces

### Data provider

```python
class PriceProvider(Protocol):
    name: str
    requests_per_hour: int          # the core's rate limiter reads this

    def fetch_prices(self, ticker: str, start: date, end: date) -> list[PriceBar]: ...
    def fetch_actions(self, ticker: str, start: date, end: date) -> list[CorporateAction]: ...

class FundamentalsProvider(Protocol):
    name: str
    requests_per_second: float

    def fetch_facts(self, cik: int, concepts: list[str]) -> list[Fact]: ...
```

Rules for a provider:

- It only fetches and translates. It does not write to the database, does not retry, and
  does not sleep. Retries, backoff, the rate limit and saving are the core's job, done once
  for all providers.
- It raises `ProviderUnavailable` (try again later), `ProviderRateLimited` (with the number
  of seconds to wait, if the provider says) or `ProviderBadData` (the answer made no sense:
  do not retry, log it).
- It returns **raw** prices. If a source only has adjusted prices, the plugin says so with
  `adjusted = True` and the core refuses to mix it with raw data.

**Example in words: `tiingo`.** One HTTPS request per ticker to Tiingo's daily prices
endpoint with a start and end date. The answer has, per day, the raw close, the split
factor and the dividend. The plugin turns each day into one `PriceBar`, and each day with a
split factor other than 1 or a dividend above 0 into a `CorporateAction`. A 429 answer
becomes `ProviderRateLimited`. An empty list for a ticker that should have data becomes
`ProviderBadData`.

**Example in words: `csv`.** Reads the same data from files in a folder. No network. This
is what the tests use, and what the one-time bulk history load uses.

**Later: `trading212`.** Not a price provider at all (their public API has account,
positions and instruments, no price history). It will be a new sixth kind, "portfolio
import", read-only. I note it here so I do not try to squeeze it into this interface.

### Universe

```python
class Universe(Protocol):
    name: str
    def members(self, as_of: date) -> list[str]: ...     # tickers
```

**Example: `theme-list`.** A YAML file per theme in the repo:

```yaml
# sim/plugins/universes/themes/ai.yaml
name: Artificial intelligence
members:
  - { ticker: NVDA, from: 2016-01-01 }
  - { ticker: MSFT, from: 2016-01-01 }
```

The plugin returns the tickers whose `from` date is on or before `as_of`. The dates matter:
calling a company an "AI stock" in 2015 because I know what happened later would be
look-ahead bias through the back door.

**Example: `sic-industry`.** Maps SEC industry codes to my sector names with a small table
(for example 2834 "pharmaceutical preparations" to Healthcare, 3760 "guided missiles" to
Defense) and returns the instruments of one sector.

### Picker

```python
class Picker(Protocol):
    name: str
    def pick(self, candidates: list[str], view: MarketView, n: int) -> list[str]: ...
```

Pickers are chained: the output of one is the input of the next. The default chain is
`quality-filter` and then one ranking picker, depending on the risk level.

**Example: `quality-filter`.** For each candidate, ask the view for the latest net income
and the latest liabilities and equity. Drop the candidate if earnings are negative or debt
is extreme (rules in `05-analysis.md`). It ignores `n`: a filter only removes.

### Weighting strategy

```python
class WeightingStrategy(Protocol):
    name: str
    def weights(self, tickers: list[str], view: MarketView) -> dict[str, float]: ...
```

Contract, checked by the core after every call, whatever the plugin: every ticker has a
weight, no weight is negative, and they sum to 1 within $10^{-9}$. A plugin that breaks
this fails the simulation with `optimiser_failed` instead of producing a wrong portfolio.

**Example: `inverse-volatility`.**

```python
@weighting("inverse-volatility")
class InverseVolatility:
    name = "inverse-volatility"

    def weights(self, tickers, view):
        vol = view.returns(tickers, lookback_days=756).std()
        inverse = 1 / vol
        return (inverse / inverse.sum()).to_dict()
```

That is a complete plugin. Caps and the core/satellite mix are applied by the core
afterwards, so every strategy gets them for free.

### Risk metric

```python
class RiskMetric(Protocol):
    name: str
    def compute(self, values: pd.Series, returns: pd.Series) -> dict[str, float]: ...
```

`values` is the daily portfolio value, `returns` its daily returns. A metric returns one or
more named numbers.

**Example: `max-drawdown`.** Divides the value series by its running maximum, subtracts 1,
and returns the smallest number as `{"max_drawdown": ...}`.

Adding a metric to the API's `Metrics` object also needs a change in `openapi.yaml`,
because the contract lists the fields. That is on purpose: the website should never be
surprised by a field.

## 4. Testing a plugin

Each kind has one shared test that every plugin of that kind must pass. It lives in
`tests/plugins/` and loops over the registry, so a new plugin is tested without writing a
new test.

| Kind | The shared test checks |
|---|---|
| Provider | Against saved example answers (files in `tests/fixtures/`): right number of bars, dates ascending, no duplicate days, splits and dividends found. No network in tests. |
| Universe | No duplicates. Members on an earlier date are a subset of what the plugin could ever return. |
| Picker | Output is a subset of the input. Same input, same output. Never returns more than `n`. |
| Weighting | Weights sum to 1, none negative, same input gives same output, works for a single ticker. |
| Risk metric | Returns only finite numbers. Works on a constant series. |

Plus the known-answer tests from `05-analysis.md` for each individual plugin.

## 5. Versioning and reproducibility

Each plugin class has a `version` string. The simulation result stores the names and
versions of the plugins it used. If I change how a strategy works, I raise its version, and
old results remain explainable: "this was computed with inverse-volatility 1".

## 6. What a plugin must never do

- Read the clock. The date comes from the `MarketView`. (A plugin that calls
  `date.today()` makes results differ from day to day.)
- Use `random` directly. If it needs randomness, it gets a seeded generator passed in.
- Keep state between calls.
- Catch and hide errors. Let them rise; the core decides whether to retry.
