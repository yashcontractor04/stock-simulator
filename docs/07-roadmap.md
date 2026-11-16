# Roadmap

The plan, one session at a time. A "step" is sized for one 2 to 3 hour Tuesday session:
about a third learning, two thirds building.

How to use it: do the steps in order. After each session, tick the box, and write three
lines in `LEARNING.md`. If a step takes two sessions, that is normal, not a failure.

## An honest word about time

I said "about 3 months". At 3 to 5 hours a week that is 40 to 65 hours. The plan below adds
up like this:

| Milestone | What I have at the end | Hours |
|---|---|---|
| M1 Setup and data | Prices and company numbers for about 500 tickers in Postgres | 16 |
| M2 Analysis core | Tested functions for returns, risk, weighting, picking | 11 |
| M3 Backtester | A backtest without look-ahead, plus the outlook | 8 |
| M4 API and job queue | The contract implemented, a worker, a CLI | 13 |
| M5 Presentable v1 | Model portfolios, live dashboard, adapter, README | 12 |
| **v1 total** | | **about 60** |
| M6 Deploy, big data, first load test | Running on the VM with 25 million rows and a baseline | 12 |
| M7+ Bottleneck loops | One interview story each | about 3 each |

So: **v1 in about 4 months** at 4 hours a week, the VM and load tests about a month after.
Three months only works with the short path below. I think the longer version is the right
call, because the bottleneck loops are the reason the project exists, and they only start
after M6. Better to arrive there with solid foundations than fast.

### The short path, if time is tight

Steps marked **(can wait)** can be skipped now and done later without breaking anything:

- 1.6 EDGAR fundamentals: pick by price-based rules only at first. Saves 3 h.
- 2.3 minimum variance: ship equal weight and inverse volatility. Saves 1.5 h.
- 4.4 ETag and rate limit headers: keep the contract test, postpone the rest. Saves 2 h.
- 4.5 scheduler: start the daily jobs by hand with the CLI. Saves 1.5 h.
- 5.4 the daily README refresh: a static screenshot first. Saves 2 h.

That brings v1 to about 50 hours.

## M0. Foundations (running until mid-December)

My Tuesday phase: SQL + indexes, EXPLAIN ANALYZE, HTTP/REST, Docker, a small to-do API.
Not planned here. The exit check is the "Ready check" at the end of `01-before-you-start.md`.

---

## M1. Project setup and data ingestion (about 16 h)

### [ ] 1.1 An empty project that runs

- **Goal:** `docker compose up` starts Postgres with the 2 GB / 1 CPU limit, and CI is green on an empty test.
- **Learn first:** compose files, volumes, resource limits. [Docker: Compose quickstart](https://docs.docker.com/compose/gettingstarted/). Video: TechWorld with Nana, "Docker Compose Tutorial".
- **Build:**
  1. Folder layout from `02-architecture.md`, `pyproject.toml` with ruff and pytest.
  2. `docker-compose.yml` with the `db` service: Postgres 16, a named volume, `mem_limit: 2g`, `cpus: 1.0`, the settings from `03-data-model.md` section 8.
  3. `.env.example`, `.gitignore`, a first test that connects and runs `select 1`.
  4. GitHub Actions workflow: ruff check, ruff format check, pytest with a Postgres service.
- **Done when:** `docker compose up -d && pytest` passes locally; the Actions run is green; `docker stats` shows the 2 GB limit.
- **Measure:** nothing yet.
- **Break it on purpose:** set `mem_limit: 64m` and watch Postgres fail to start. Read the log and find the reason.
- **Interview point:** "I capped the database at 2 GB on purpose, so performance problems show up on my laptop and not only in theory."

### [ ] 1.2 Migrations and the first tables

- **Goal:** `sim db migrate` creates the market data tables from numbered SQL files.
- **Learn first:** what a migration is, primary keys, why key column order matters. [use-the-index-luke.com: Anatomy of an index](https://use-the-index-luke.com/sql/anatomy). Video: Hussein Nasser, "Database Indexing Explained".
- **Build:**
  1. A `schema_migrations` table and a small runner: apply files in `sql/migrations/` in order, each in a transaction, record the name.
  2. `0001_market_data.sql`: `instruments`, `price_bars`, `corporate_actions`, `ingestion_runs`, `ingestion_state`.
  3. The `sim` CLI entry point with the one command `db migrate`.
  4. Database roles `sim_owner`, `sim_api`, `sim_worker`.
- **Done when:** running migrate twice changes nothing the second time; a test creates a fresh database and migrates it; `\d price_bars` in psql shows the primary key.
- **Measure:** nothing yet.
- **Break it on purpose:** put a syntax error in the second statement of a migration. Check that the first statement was rolled back too.
- **Interview point:** "Schema changes are plain SQL files applied in order inside transactions, so a failed migration leaves nothing half done."

### [ ] 1.3 The provider interface and two providers

- **Goal:** fetch one ticker's prices, splits and dividends through a plugin, from Tiingo and from a file.
- **Learn first:** Python Protocols, calling an HTTP API with `httpx`. [Tiingo end-of-day docs](https://www.tiingo.com/documentation/end-of-day). Video: ArjanCodes, "Protocol or ABC in Python".
- **Build:**
  1. The data types and the `PriceProvider` Protocol from `06-plugins.md`, plus the registry.
  2. `csv` provider: reads bars and actions from a folder.
  3. `tiingo` provider: one request per ticker, translate the answer, map errors to the three provider exceptions.
  4. Save two real Tiingo answers as fixture files (one with a split, one with dividends). Tests run against the files, never the network.
- **Done when:** both providers pass the shared provider test; a small script prints AAPL's 2020 4-for-1 split as a `CorporateAction`.
- **Measure:** how long one Tiingo request takes (write it down, it matters for the backfill plan).
- **Break it on purpose:** use a wrong API key, then a ticker that does not exist. Each must give a different, clear exception.
- **Interview point:** "Data sources sit behind one small interface. Tests use a file-based provider, so they need no network and never hit a rate limit."

### [ ] 1.4 Ingestion that is safe to run twice

- **Goal:** an ingestion run stores prices exactly once, respects the hourly limit, and continues where it stopped.
- **Learn first:** idempotency, `INSERT ... ON CONFLICT`, retries with exponential backoff, token bucket. [Postgres docs: INSERT, ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT). Video: ByteByteGo, "Rate Limiting Algorithms" (search the channel).
- **Build:**
  1. `repositories/prices.py`: bulk insert with `on conflict do nothing`.
  2. A rate limiter that reads `requests_per_hour` from the provider.
  3. Retry wrapper: `ProviderUnavailable` retries with 30 s, 2 min, 8 min; `ProviderBadData` does not.
  4. The ingestion loop: ask `ingestion_state` who is behind, fetch, insert, update state, record an `ingestion_runs` row.
  5. `sim ingest prices --tickers AAPL,MSFT --since 2006-01-01`.
- **Done when:** running the same command twice adds 0 rows the second time; killing it halfway and restarting finishes without duplicates or gaps; tests cover all three with the csv provider.
- **Measure:** rows per second for single-row inserts vs. one multi-row insert vs. `COPY`. First small before/after note.
- **Break it on purpose:** a fake provider that fails every third call. The run must still complete, and the log must show the waits.
- **Interview point:** "Ingestion is idempotent and resumable: I can kill it at any point and run it again, and the result is the same."

### [ ] 1.5 The universe and the first real backfill

- **Goal:** about 500 stocks and 30 ETFs with 20 years of daily prices in the database, and a report on data quality.
- **Learn first:** survivorship bias (re-read `01-before-you-start.md`), trading calendars. Video: Ben Felix, "Survivorship Bias" (search the channel) or any short explainer on the topic.
- **Build:**
  1. A seed file for `instruments` and the `us-large` and `core-etfs` universes. Source of the list: the SEC's `company_tickers.json` for names and CIKs, filtered by a list of large companies I assemble once by hand.
  2. Start the backfill. At 50 requests an hour it runs for about a day. Let it.
  3. `sim data check`: per instrument, count days, find gaps against the SPY calendar, find one-day moves above 40% that have no split.
- **Done when:** the check reports no unexplained gaps for at least 95% of instruments, and I have written down what is wrong with the rest.
- **Measure:** table and index size (`pg_total_relation_size`), compared with the estimate in `03-data-model.md`.
- **Break it on purpose:** delete one instrument's rows for one month by hand. The check must find the gap and a re-run of ingestion must repair it.
- **Interview point:** "My universe is today's companies, which is survivorship bias. I know it, the results say it, and the schema already has membership dates for the fix."

### [ ] 1.6 Company numbers from SEC EDGAR **(can wait)**

- **Goal:** net income, liabilities and equity with filing dates, and a sector for each company.
- **Learn first:** what 10-K and 10-Q are, the EDGAR company facts API. [SEC: EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). Look at one company's JSON in the browser before writing code.
- **Build:**
  1. `0002_fundamentals.sql`: `fundamentals` with the "as of" index.
  2. `edgar` provider: company facts for one CIK, with the required `User-Agent`, max 10 requests a second.
  3. Keep only a short list of concepts. Handle that companies use different names for the same thing (two or three alternative revenue and income tags).
  4. SIC code to sector table; fill `instruments.sector`.
  5. `repositories/fundamentals.py` with the as-of query.
- **Done when:** for three companies I checked by hand, "net income as of 2019-03-01" equals the number in the filing that was public then; the as-of test with a later correction passes.
- **Measure:** `EXPLAIN ANALYZE` of the as-of query with and without the second index. Keep both plans.
- **Break it on purpose:** drop the `filed_at <= :as_of` condition and show with a test that a backtest date now sees a future number.
- **Interview point:** "Every fundamental value is stored with the date it became public, and every query takes an as-of date. That is how I keep look-ahead bias out at the database level."

---

## M2. Analysis core (about 11 h)

Pure functions on pandas and numpy. No database, no network. Every function gets a test with
numbers I can check by hand (`05-analysis.md` has them).

### [ ] 2.1 Returns

- **Goal:** correct daily total returns from raw prices, splits and dividends.
- **Learn first:** simple vs. log returns. Video: any 10-minute "log returns explained" (for example from the channel "QuantPy"). pandas: [Time series user guide](https://pandas.pydata.org/docs/user_guide/timeseries.html), skim.
- **Build:** `core/returns.py`: total returns for one instrument, a returns table for many, gap detection (raise, do not fill), CAGR.
- **Done when:** the three test examples from `05-analysis.md` section 2 pass; AAPL's return on its 2020 split day is a normal number.
- **Measure:** time to build a 10-year returns table for 30 tickers from the database. First number for later comparison.
- **Break it on purpose:** remove the split from `corporate_actions` and look at the return series. Then plot it.
- **Interview point:** "I store raw prices and apply splits and dividends when reading. A new dividend adds one row instead of rewriting history."

### [ ] 2.2 Risk and performance metrics

- **Goal:** volatility, max drawdown, VaR, Expected Shortfall, Sharpe as risk metric plugins.
- **Learn first:** quantiles from Stochastik, then VaR. Video: "Value at Risk explained" by Ryan O'Connell, CFA (search), about 10 minutes.
- **Build:** the `RiskMetric` Protocol, four plugins, the shared metric test.
- **Done when:** all known-answer tests pass; property tests hold (drawdown never positive, ES never above VaR).
- **Measure:** nothing.
- **Break it on purpose:** compute VaR assuming a normal distribution and compare with the historical one for SPY in 2008. Write down the difference: that is fat tails in one number.
- **Interview point:** "VaR is just a quantile. I show Expected Shortfall next to it because VaR says nothing about how bad the tail is."

### [ ] 2.3 Covariance and weighting

- **Goal:** three weighting plugins that pass the same contract test.
- **Learn first:** covariance matrix, portfolio variance $w^\top \Sigma w$. Video: search "portfolio variance two assets" and watch one worked example. For the optimiser: [scipy.optimize.minimize docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html), the SLSQP example.
- **Build:** `equal-weight`, `inverse-volatility`, then `minimum-variance` **(can wait)** with bounds and the sum-to-one constraint.
- **Done when:** the two-asset known answers from `05-analysis.md` pass; every plugin passes the shared weighting test.
- **Measure:** how long minimum variance takes for 15 and for 100 assets.
- **Break it on purpose:** run minimum variance without the cap on real data and look at the weights. Then with only 30 days of history.
- **Interview point:** "Minimum variance is the most sensitive to estimation noise, so I cap weights, and I keep 1/N as the baseline every other strategy must beat."

### [ ] 2.4 Picking, risk limits and warnings

- **Goal:** from a universe and a risk level to final weights, with warnings.
- **Learn first:** re-read `05-analysis.md` sections 5 and 7 and `06-plugins.md` section 2.
- **Build:**
  1. `MarketView` with a hard cut at `as_of`, backed by the repositories.
  2. Universe plugins (`us-large`, `core-etfs`, `sic-industry`, `theme-list`).
  3. Pickers: `quality-filter` (if 1.6 is done), `low-volatility-rank`, `momentum-rank`.
  4. Caps, core/satellite mix, the six warnings.
- **Done when:** the hand-made six-company universe test passes; the caps example passes; asking the view for a later date raises an error.
- **Measure:** nothing.
- **Break it on purpose:** give a theme list a company with a `from` date in the future and check it is not picked.
- **Interview point:** "Strategies never touch the database. They get a view of the data that ends at the decision date, so they cannot look ahead even by mistake."

---

## M3. Backtester (about 8 h)

### [ ] 3.1 Buy and hold against the benchmark

- **Goal:** a backtest that returns daily values for the portfolio and for SPY.
- **Learn first:** re-read `05-analysis.md` section 8. Video: search "backtesting pitfalls look-ahead bias" and watch one short explainer.
- **Build:** `core/backtest.py`: buy on day one, carry shares, apply splits, reinvest dividends, value daily. Run the benchmark through the same code.
- **Done when:** the one-stock test passes on every day; my SPY backtest matches SPY's published total return for one calendar year within half a percentage point.
- **Measure:** run time for 10 years × 30 instruments.
- **Break it on purpose:** ignore dividends and compare SPY's 10-year result. The gap is what "price return vs. total return" means.
- **Interview point:** "I check my backtester against a known answer: SPY's published total return."

### [ ] 3.2 Rebalancing and the look-ahead tests

- **Goal:** yearly and quarterly rebalancing, and proof that no decision uses future data.
- **Learn first:** nothing new. This session is about testing.
- **Build:** rebalance dates, re-pick and re-weight on those dates with a view cut at the day before, the "poisoned future" test.
- **Done when:** the two-stock rebalancing example passes; the poisoned future test passes.
- **Measure:** nothing.
- **Break it on purpose:** introduce an off-by-one (use the same day's close for the decision). The poisoned future test must catch it. If it does not, the test is not good enough yet.
- **Interview point:** "I have a test that replaces all future prices with nonsense and checks that past decisions do not change."

### [ ] 3.3 The outlook

- **Goal:** a seeded block bootstrap that returns percentile bands per month.
- **Learn first:** bootstrap. Video: StatQuest, "Bootstrapping Main Ideas!!!". Then [numpy: Random Generator](https://numpy.org/doc/stable/reference/random/generator.html).
- **Build:** `core/montecarlo.py` with a passed-in generator; thinning of long series to 400 points; the golden test (fixed small data set, fixed seed, stored result).
- **Done when:** the three tests from `05-analysis.md` section 9 pass; the golden file exists.
- **Measure:** time for 1,000 paths × 10 years with a Python loop vs. one vectorised numpy call. Good first optimisation note.
- **Break it on purpose:** use `numpy.random.seed` and the global functions in one place, run two simulations in different order, and watch the results change.
- **Interview point:** "Results are reproducible: one seeded generator is passed down, and the seed and the data version are stored with every result."

---

## M4. API and job queue (about 13 h)

### [ ] 4.1 The API skeleton

- **Goal:** FastAPI answers `/healthz`, `/readyz` and `/v1/meta/options`, with tokens and the error format from the contract.
- **Learn first:** [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) up to "Dependencies"; connection pools. Video: Hussein Nasser, "Database Connection Pooling" (search the channel).
- **Build:** the app, a psycopg connection pool (start with max 5), bearer token check with constant-time compare, one error handler that produces the problem format, the `api` service in compose.
- **Done when:** `curl` without a token gets the 401 from the contract; with the service token on an admin path, 403; options match the contract example's shape.
- **Measure:** nothing.
- **Break it on purpose:** set the pool size to 1 and send 20 parallel requests to an endpoint that sleeps in SQL (`pg_sleep`). Watch them queue.
- **Interview point:** "The API never opens a connection per request. A small pool is shared, because each Postgres connection costs memory I do not have."

### [ ] 4.2 The job queue and the worker

- **Goal:** a worker process that claims jobs, sends heartbeats, retries and recovers from a crash.
- **Learn first:** row locks and `SKIP LOCKED`. Read: "What is SELECT FOR UPDATE SKIP LOCKED" on the 2ndQuadrant or Crunchy Data blog (search the title). Look at the portfolio repo's queue functions for a second example.
- **Build:** `0003_jobs.sql` with the partial index; `repositories/jobs.py` (enqueue, claim, heartbeat, complete, fail, requeue stale); the worker loop with a handler per job kind and a time limit; graceful stop on SIGTERM.
- **Done when:** tests show: two workers never get the same job (run two claims in two transactions); a failed retryable job comes back after its wait; a job without heartbeat for 90 s is re-queued.
- **Measure:** `EXPLAIN ANALYZE` of the claim query with 100,000 finished jobs in the table, with and without the partial index.
- **Break it on purpose:** `docker kill` the worker in the middle of a job. Watch the job come back and finish.
- **Interview point:** "My queue is a Postgres table. `FOR UPDATE SKIP LOCKED` gives each worker a different row, and a heartbeat brings jobs back if a worker dies."

### [ ] 4.3 Simulations over the API

- **Goal:** `POST /v1/simulations` returns 202 and the result appears under `GET`.
- **Learn first:** the 202 pattern and idempotency keys. Video: ByteByteGo, "What is Idempotency?" (search), or the Stripe blog post "Designing robust and predictable APIs with idempotency".
- **Build:** `0004_simulations.sql`; the `simulate` service that runs M2 and M3 and builds the result object; the three endpoints; idempotency key handling; the result cache through the unique pair.
- **Done when:** the same request twice creates one job; the same key with other inputs gives 409; a finished result validates against the contract's schema.
- **Measure:** end-to-end time of one simulation, split into: load prices, compute, save.
- **Break it on purpose:** start a simulation, ingest one new day of prices, send the same request again. A new result must be computed, because `data_version` changed.
- **Interview point:** "A result is cached under the hash of its inputs plus the data version. New data means a new key, so I never have to delete cache entries."

### [ ] 4.4 Contract test, caching headers, rate limit

- **Goal:** CI fails when code and `openapi.yaml` disagree; read endpoints send `ETag`; limits are enforced.
- **Learn first:** [MDN: HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching), the section on validation; token bucket again.
- **Build:** the contract test from `04-api.md` section 9 (this one first, it is not optional); `ETag` and `If-None-Match` **(can wait)**; the token bucket and `RateLimit-*` headers **(can wait)**; the queue-full check.
- **Done when:** renaming a field in code turns the test red; a second `GET` with the ETag returns 304; the 121st request in a minute gets 429.
- **Measure:** response time and bytes for prices with and without a matching `If-None-Match`.
- **Break it on purpose:** build the ETag without `data_version`, ingest a day, and see the API serve stale prices with a 304.
- **Interview point:** "The API contract is written first, and a CI test compares it with what the code generates, so the two cannot drift."

### [ ] 4.5 CLI, admin jobs and the scheduler

- **Goal:** everything I do by hand goes through jobs; daily jobs start by themselves.
- **Learn first:** [Typer tutorial](https://typer.tiangolo.com/tutorial/), first pages.
- **Build:** admin endpoints; turn ingestion from 1.4 into job handlers; CLI commands from `02-architecture.md`; the `schedules` table and the once-a-minute check in the worker **(can wait)**.
- **Done when:** `sim ingest prices` creates a job the worker runs; `sim jobs list` shows it; a schedule set one minute ahead fires once, not twice.
- **Measure:** nothing.
- **Break it on purpose:** run two workers with the scheduler on. A daily job must still be created only once. Find out why it is, or fix it.
- **Interview point:** "The CLI and the API create the same jobs, so there is one code path and everything that ever ran is visible in one table."

---

## M5. Presentable v1 (about 12 h)

### [ ] 5.1 The three model portfolios

- **Goal:** three portfolios fixed on a start date and valued for every trading day since.
- **Learn first:** backtest vs. forward test (glossary). Decide the start date and the exact rule table in `05-analysis.md` section 7 **before** looking at any result. Write the date into the README.
- **Build:** `0005_models.sql`; `sim models rebuild` (create from rules as of the start date, store shares); the `update_model_portfolios` job (add one `model_values` row per day, apply splits and dividends); `GET /v1/model-portfolios`.
- **Done when:** running the daily update twice adds no second row; the values equal a backtest over the same days.
- **Measure:** time of the daily update.
- **Break it on purpose:** skip three days of updates, then run it. It must fill all three days, not only the last.
- **Interview point:** "The model portfolios are a forward test. They were fixed on a published date, so I cannot tune them to look good afterwards."

### [ ] 5.2 The daily snapshot

- **Goal:** one small JSON document per day, published to Supabase.
- **Learn first:** least privilege. Read the migration `20261116000001_sim_snapshots.sql` in the portfolio repo and its tests.
- **Build:** the snapshot builder (thinning to 400 points, "Other" row, outlook per month); `GET /v1/snapshot/latest`; the `export_snapshot` job calling `sim.publish_snapshot`; in Supabase: `alter role sim_publisher login password '...'` once, by hand.
- **Done when:** the snapshot validates against the contract; it is under 256 KB; the row appears in `sim_snapshots`; publishing twice keeps one row for that day.
- **Measure:** snapshot size in bytes.
- **Break it on purpose:** try `select * from profiles` with the `sim_publisher` connection. It must be refused.
- **Interview point:** "The server has no open ports. It pushes one small document a day, with a database role that can call exactly one function."

### [ ] 5.3 The adapter in the portfolio repo

- **Goal:** a run started on my website reaches the simulator and comes back as a result.
- **Learn first:** the docstring in `portfolio/worker/worker/runners/stock_sim.py` and `04-api.md` section 7. [httpx: Mock transports](https://www.python-httpx.org/advanced/transports/#mock-transports).
- **Build (in the portfolio repo):** `run()` as described in the docstring; tests with a fake transport for: success, simulation failed, 429, timeout, simulator down.
- **Done when:** the tests pass; locally, with both compose projects on `sim-net`, a demo run on the site shows a real result; my output has the same shape as the website's sample data.
- **Measure:** time from click to result.
- **Break it on purpose:** stop the simulator and start a run. The site must show a clear "try again later", and the job must be retried.
- **Interview point:** "Two services talk through a written contract. The adapter maps errors into 'retry later' and 'do not retry', and sends an idempotency key so a retry never runs the work twice."

### [ ] 5.4 The README showcase

- **Goal:** someone who only sees the GitHub page understands the project in a minute.
- **Learn first:** [GitHub Actions: schedule](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule).
- **Build:** fill the README skeleton; a screenshot or GIF of the dashboard; a small script that reads the public snapshot and rewrites the performance table between two marker comments; a daily workflow that runs it and commits **(can wait: start with a static table)**.
- **Done when:** the README renders with diagram and table; the workflow ran once and changed only the marked block.
- **Measure:** nothing.
- **Break it on purpose:** make the snapshot unreachable (wrong URL). The workflow must fail visibly and leave the README untouched.
- **Interview point:** "The README shows live performance, refreshed daily by a workflow that only needs a public read-only key."

### [ ] 5.5 Going live

- **Goal:** the website shows real data instead of sample data.
- **Build:** apply the portfolio migration and seed in Supabase; `status: live` in the manifest; set `SIM_DATA=live` in Vercel; rebuild the portfolio worker with the extra compose file. Checklist in the portfolio's `docs/ROADMAP.md`, item 19.
- **Done when:** the acceptance line of that item passes.
- **Measure:** nothing.
- **Break it on purpose:** publish a snapshot with `schema_version: 2` by hand. The site must show "no data", not a broken page.
- **Interview point:** "Going live was one environment variable, because the pages were built against the contract's examples from the start."

---

## M6. Deploy, big data, first load test (about 12 h)

### [ ] 6.1 The VM

- **Goal:** the simulator runs on the Oracle VM next to the portfolio worker.
- **Learn first:** Docker networks. [Docker: Networking overview](https://docs.docker.com/engine/network/). Video: NetworkChuck, "Docker networking is CRAZY" (search).
- **Build:** production compose file (no published ports, `sim-net` external, limits from `02-architecture.md` section 7, non-root, restart policy); secrets in `.env` on the VM; a deploy workflow over SSH; nightly `pg_dump` to the VM's disk.
- **Done when:** from the portfolio worker container `curl http://sim-api:8000/healthz` works; from outside the VM nothing answers; a reboot brings everything back.
- **Measure:** `docker stats` at rest: RAM per container against the budget.
- **Break it on purpose:** try to reach the database from the portfolio worker container. It must not resolve.
- **Interview point:** "The API and the database are on different Docker networks. The only thing another service can reach is the API, and nothing is reachable from the internet."

### [ ] 6.2 Seeing inside

- **Goal:** logs, metrics and slow queries are available before I load test.
- **Learn first:** percentiles, why averages lie. Video: search "why averages are misleading latency percentiles" (for example a talk by Gil Tene, first 15 minutes). [Postgres docs: pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html).
- **Build:** JSON logs with request and job ids; `/metrics` with request duration histograms per route, job durations, queue length, cache hits; enable `pg_stat_statements` and slow query logging; a `sim stats` command that prints the top 10 queries by total time.
- **Done when:** I can answer "what was the p95 of the prices endpoint in the last test?" and "which query used the most time?" from data.
- **Measure:** this step is the measuring tool.
- **Break it on purpose:** add a `pg_sleep(0.5)` to one query and find it using only the tools from this step.
- **Interview point:** "Before optimising anything I made it measurable: p50 and p95 per route and the database's own statistics on every query."

### [ ] 6.3 The big data load

- **Goal:** about 5,000 instruments and about 25 million price rows in the 2 GB database.
- **Learn first:** `COPY`, and why bulk loads drop indexes first. [Postgres docs: Populating a Database](https://www.postgresql.org/docs/current/populate.html).
- **Build:** get a bulk history file (Stooq's download, after reading its terms; fallback: slow backfill from Tiingo over several weeks); convert to the `csv` provider's format; load with `COPY`; mark these instruments as "history only" (not updated daily).
- **Done when:** row count and sizes match the estimate within 20%; `sim data check` runs on the full set.
- **Measure:** load time with indexes in place vs. creating the index after the load; final table and index sizes; cache hit ratio from `pg_statio_user_tables`.
- **Break it on purpose:** run `select count(*) from price_bars where day = '2020-03-16'` and read the plan. This is the query the primary key cannot help.
- **Interview point:** "Table plus index is bigger than the database's memory, so which pages a query touches now decides if it takes milliseconds or seconds."

### [ ] 6.4 The first load test

- **Goal:** a repeatable test and a baseline in `BENCHMARKS.md`.
- **Learn first:** [k6: Get started](https://grafana.com/docs/k6/latest/get-started/) and "Running k6". Video: the official "k6 in 10 minutes" style intro on the Grafana channel (search).
- **Build:** a k6 script with three scenarios: (a) price reads for a few popular tickers, (b) price reads for random tickers across all 5,000, (c) simulations with a small set of repeating inputs. Run from my Mac through an SSH tunnel. Fill the setup table in `BENCHMARKS.md`.
- **Done when:** the same test run twice gives similar numbers; the baseline table is filled.
- **Measure:** requests per second, p50, p95, error rate per scenario; CPU and RAM per container during the test.
- **Break it on purpose:** raise the load until something fails. Write down what failed first. That is loop 1.
- **Interview point:** "I load test from outside the server through an SSH tunnel, so the test tool does not steal CPU from the thing I measure."

---

## M7+. Bottleneck loops (about 3 h each)

Each loop: load test, measure, find the **biggest** bottleneck, change **one** thing, measure
again, write the entry in `BENCHMARKS.md`. The order comes from the measurements, not from
this list. These are the candidates I expect:

| Candidate | The symptom I would see | What I would try | Concepts |
|---|---|---|---|
| Connection pool | Requests wait although the database is idle, or "too many connections" | Tune pool size; later PgBouncer | pooling |
| Cold cache on random tickers | Scenario (b) far slower than (a); many disk reads | Covering index, `CLUSTER`, more or less `shared_buffers` | page cache, index-only scans |
| Many small queries | A simulation sends 30 queries, one per ticker | One query with `= any(...)` | N+1 problem |
| Repeated identical reads | The same series loaded again and again | In-process cache keyed by ticker and `data_version` | caching, invalidation |
| Daily update slow | "All instruments for one day" scans everything | BRIN or `(day)` index, then partitioning by year | partition pruning |
| Worker memory | pandas builds a huge table, the container is killed | Load only needed columns and dates, `float32` | memory profiling |
| JSON building | CPU time in serialisation for long price lists | Build JSON in Postgres, or a faster encoder | profiling |
| Queue polling | Unlikely. Only if polling shows up in the statistics | `LISTEN/NOTIFY`; Redis only if that is not enough | pub/sub |

For every loop the same seven fields apply; the last four go into the benchmark entry:
goal (the symptom gone), concept to learn (from the table), build (one change), done (the
after numbers), measure (same scenario), break it (undo the change and confirm the numbers
go back), interview point (the last line of the entry).

Three good loops are enough to carry an interview. Five is a strong project.

## Later, as plugins

Not planned in detail. Each is a self-contained addition:

- **Honest universe:** historical index membership and delisted tickers, to remove the survivorship warning.
- **Strategy experiments:** timing rules and rebalancing comparisons (`05-analysis.md` section 10).
- **Trading 212 import:** read-only import of my real positions through their public API, shown next to a model portfolio.
- **Europe:** a second universe and a price provider that covers European exchanges, plus currencies.
- **AI news sentiment:** a picker that scores recent news. Hard to do without look-ahead; the news must carry timestamps.
- **Admin pages:** on the website, sending `admin_command` jobs through the portfolio's queue.
- **Public read-only API:** through Cloudflare Tunnel, once I have a domain.
