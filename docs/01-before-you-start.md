# Before I start

What I need to know, install and sign up for before milestone M1. Most of the concepts are
covered by my Tuesday foundations phase (SQL + indexes, EXPLAIN ANALYZE, HTTP/REST, Docker,
a small to-do API). This file is the checklist that connects that phase to the project.

A note on the links: the written links are official pages that stay stable. For videos I
give the channel and the title to search for, because video links change.

## 1. Concepts, and how well I need them

"Enough" means: I can explain it to a friend in two minutes and have used it once.

| Concept | Enough for the start is... | Good visual resource |
|---|---|---|
| SQL joins, GROUP BY, subqueries | I can write them without looking things up. Refresh from my databases module. | [pgexercises.com](https://pgexercises.com/) (practice in the browser) |
| Indexes (B-tree) | I know an index is a sorted copy of some columns, and why column order matters. | [use-the-index-luke.com](https://use-the-index-luke.com/), chapters 1 and 2. Video: Hussein Nasser, "Database Indexing Explained" |
| EXPLAIN ANALYZE | I can read a plan and tell a sequential scan from an index scan. | [Postgres docs: Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html), then paste plans into [explain.dalibo.com](https://explain.dalibo.com/) to see them drawn |
| Transactions and locks | I know what BEGIN/COMMIT do and that a row can be locked. | Video: Hussein Nasser, "ACID explained" |
| HTTP and REST | Methods, status codes (200, 202, 304, 404, 409, 422, 429, 503), headers, JSON. | [MDN: An overview of HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview). Video: Fireship, "RESTful APIs in 100 Seconds" |
| Docker | Image vs. container, a Dockerfile, a compose file with two services, volumes. | [Docker: Get started](https://docs.docker.com/get-started/). Video: Fireship, "Docker in 100 Seconds", then TechWorld with Nana, "Docker Tutorial for Beginners" |
| FastAPI | A route, a pydantic model for input and output, dependency injection for the database. | [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/), "First Steps" to "Request Body" |
| Jinja2 and HTMX | A template with a loop and a block, and one HTMX attribute that swaps part of a page. Needed from M5. | [Jinja: Template Designer Documentation](https://jinja.palletsprojects.com/en/stable/templates/), first sections. [htmx.org: docs](https://htmx.org/docs/), "Introduction" to "Swapping". Video: Fireship, "htmx in 100 seconds" |
| Cookies, sessions, CSRF | I can say what a session cookie is and why another website must not be able to use mine. Needed from M5. | [MDN: Using HTTP cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies). [OWASP: CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), the first part |
| pytest | Writing a test, fixtures, parametrize. | [pytest: Get started](https://docs.pytest.org/en/stable/getting-started.html) |
| pandas basics | A DataFrame with a date index, `pct_change`, `rolling`, `groupby`. | [10 minutes to pandas](https://pandas.pydata.org/docs/user_guide/10min.html) |
| Stochastik I already have | Random variables, expected value, variance, covariance, quantiles, law of large numbers, confidence intervals. All used in `05-analysis.md`. | Video: StatQuest, "Bootstrapping Main Ideas!!!" for the one new idea |

Things I do **not** need before starting, because a milestone teaches them when needed:
partitioning, connection pooling, `FOR UPDATE SKIP LOCKED`, Prometheus, k6, GitHub Actions
deploys, Cloudflare Tunnel.

## 2. Accounts

| Account | Why | Cost | Status |
|---|---|---|---|
| GitHub | repo, Actions | free | have it |
| Tiingo | daily prices | free plan: about 50 requests an hour, 1,000 a day | **create before M1** |
| SEC EDGAR | company numbers | free, no account. Needs a `User-Agent` header with my name and email, max 10 requests a second | nothing to do |
| Oracle Cloud | the VM | Always Free | have it (from the portfolio) |
| A domain | the public address | free first year through the GitHub Student Developer Pack, then about €10 to €15 a year | **not yet**. Nothing before M6 needs it |
| Cloudflare | the tunnel, HTTPS, cache | free | create when I have the domain |

Terms I must read once myself and note here with the date:

- [ ] Tiingo terms for the free plan. It is for personal, internal use, and my site is
      public. The pages show values of whole portfolios, not raw prices of single stocks.
      The one endpoint that returns raw prices stays admin-only until I am sure this is
      allowed. If it is not: ask Tiingo, or switch the provider plugin. Read date: ______
- [ ] SEC fair access policy ([sec.gov, Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)). Read date: ______
- [ ] Stooq, if I use its bulk download for the big history load. Read date: ______
- [ ] yfinance is unofficial. It reads Yahoo pages that Yahoo's terms reserve for personal
      use. I keep it as an emergency fallback only and never for the public dashboard.

## 3. Tools on my Mac

- Python 3.12 or newer, with `uv` or plain `venv` + `pip`.
- Docker Desktop (already there for the portfolio worker).
- `psql` (the Postgres command line client) or DataGrip.
- `ruff` for lint and format, `pytest` for tests.
- Later: `k6` for load tests (M6).

Check: `docker compose version`, `python3 --version` and `psql --version` all print something.

## 4. Glossary

### Finance

| Term | Meaning |
|---|---|
| Ticker | The short code of a stock, like MSFT. |
| ETF | A fund that holds many stocks and trades like one stock. SPY holds the 500 companies of the S&P 500. |
| Benchmark | What I compare against. Here: buying SPY and holding it. |
| Return | The change in value as a fraction. From 100 to 110 is a return of 0.10. |
| Log return | $\ln(P_t / P_{t-1})$. Handy because log returns over several days simply add up. |
| Volatility | How much returns jump around: their standard deviation, usually per year. |
| Drawdown | How far the value has fallen from its highest point so far. |
| CAGR | Growth per year, if growth had been the same every year. |
| Sharpe ratio | Return above a safe interest rate, divided by volatility. "Return per unit of risk". |
| Value at Risk (VaR) | "On 95 of 100 days I lose less than this." A quantile of the return distribution. |
| Expected Shortfall | The average loss on the other 5 days. |
| Split | A company cuts each share into several. The price drops, the value does not. |
| Dividend | Cash a company pays per share. The price drops by about that amount on that day. |
| Adjusted price | A price series corrected for splits and dividends, so returns are right. |
| Rebalancing | Selling winners and buying losers to get back to the planned weights. |
| Backtest | Running a strategy on past data. |
| Forward test | Fixing a strategy today and watching what really happens. |
| Universe | The list of stocks the tool may pick from. |
| Fundamentals | Numbers from a company's reports: earnings, debt, revenue. |
| 10-K, 10-Q | A US company's yearly and quarterly report, filed with the SEC. |
| CIK, SIC | The SEC's id for a company, and its 4-digit industry code. |
| Core + satellite | Most money in broad funds (core), a smaller part in single picks (satellites). |

### Backend

| Term | Meaning |
|---|---|
| API | The set of requests a program accepts. Here: HTTP requests with JSON. |
| Endpoint | One address of the API, like `GET /v1/simulations/{id}`. |
| Contract | The written promise of what the API accepts and returns (`openapi.yaml`). |
| Job queue | A list of work waiting to be done by a worker. |
| Worker | A process that takes jobs from the queue and does them. |
| Idempotent | Doing it twice has the same effect as doing it once. |
| Backoff | Waiting longer after each failed try: 30 s, 2 min, 8 min. |
| Rate limit | A cap on requests per time, on my API or on someone else's. |
| Cache | A short-term memory for answers, so the same question is not computed twice. |
| Invalidation | Deciding that a cached answer is too old to use. |
| Index | A sorted helper structure that lets the database find rows without reading the whole table. |
| Query plan | The steps the database chose to answer a query. `EXPLAIN` shows it. |
| Sequential scan | Reading every row of a table. Fine for small tables, painful for 25 million rows. |
| Partitioning | Splitting one big table into smaller ones (for example one per year) that look like one. |
| Connection pool | A small set of open database connections that requests share. |
| Transaction | A group of changes that happen all together or not at all. |
| Migration | A numbered file that changes the database structure. |
| p50, p95 | The median response time, and the time 95% of requests stay under. |
| Plugin | A piece of code behind a fixed interface that can be added without changing the core. |
| ETag | A fingerprint of a response. The caller can ask "has it changed?" instead of downloading again. |
| Template | An HTML file with placeholders that the server fills in before sending it. |
| HTMX | A small script that lets a page replace parts of itself with HTML from the server. |
| Session cookie | A random id the server gives my browser after login, sent back with every request. |
| CSRF | An attack where another website makes my browser send a request with my cookie. |
| Tunnel | An outgoing connection from my server to a provider, through which visitors' requests come back in. No open port needed. |
| CSP | Content Security Policy: a header that tells the browser which scripts and styles it may load. |

## 5. The four traps

These are the classic ways a backtest lies. Each has a matching exercise in the roadmap.

### Look-ahead bias

Using information that was not known yet on that day.

Example: a company's results for the quarter ending 31 March are published on 5 May. If my
backtest uses them on 1 April, it knows the future.

My defence: every fundamental value is stored with its **filing date**, and every query
takes an "as of" date: `... where filed_at <= :as_of`. The backtester only ever passes
today's simulated date. There is a test that fails if a value appears one day early.

### Survivorship bias

Looking only at companies that still exist.

Example: if I pick from "today's 500 largest companies" for a backtest starting in 2008, I
have already removed everyone who went bankrupt since. The result looks better than reality.

My defence in v1: honesty. The result carries a `survivorship_bias` warning. Later: a
universe with start and end dates per member, and delisted tickers in the data.

### Overfitting

Tuning rules until the past looks great. The more knobs I turn, the more I fit noise.

My defence: few rules, chosen before I look at results and written down in
`05-analysis.md`. And the forward test: the three model portfolios cannot be tuned after
their start date.

### Splits and dividends

Example: a 4-for-1 split makes the price fall by 75% overnight. Without correction, that
looks like a crash. Ignoring dividends does the opposite: it makes dividend-paying stocks
look worse than they were.

My defence: raw prices and a separate table of splits and dividends. Returns are computed
from both. Test: a known split day must show a normal daily return.

## 6. Ready check

I start M1 when all of these are true:

- [ ] The to-do API capstone from the foundations phase runs in Docker with Postgres.
- [ ] I have read one query plan and can say why it used, or did not use, an index.
- [ ] I have a Tiingo key and fetched one ticker with `curl`.
- [ ] I have fetched one company from EDGAR with `curl` and a proper `User-Agent`.
- [ ] I have read `00-overview.md`, `02-architecture.md` and the first milestone of the roadmap.
