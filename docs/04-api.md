# API

`openapi.yaml` is the exact contract. This file is the readable companion: what the
endpoints are for, how the pieces behave, and how I keep code and contract the same.

To look at the contract nicely: paste `openapi.yaml` into
[editor.swagger.io](https://editor.swagger.io/), or later open `/docs` on the running API.

## 1. Endpoints at a glance

| Endpoint | Who | What |
|---|---|---|
| `GET /healthz` | anyone on the network | The process runs. |
| `GET /readyz` | anyone on the network | The database answers. Shows `data_version`. |
| `GET /v1/meta/options` | service | Risk levels, industries, themes, limits. |
| `POST /v1/simulations` | service | Order a simulation. Answers 202 with an id. |
| `GET /v1/simulations/{id}` | service | Status, and the result when ready. |
| `DELETE /v1/simulations/{id}` | service | Cancel. |
| `GET /v1/model-portfolios` | service | The three live portfolios, short form. |
| `GET /v1/snapshot/latest` | service | The daily snapshot, as sent to Supabase. |
| `GET /v1/instruments` | service | Search stocks and ETFs. |
| `GET /v1/instruments/{ticker}/prices` | service | Daily prices of one instrument. |
| `POST /v1/admin/jobs` | **admin** | Queue ingestion, model update, snapshot export. |
| `GET /v1/admin/jobs`, `GET /v1/admin/jobs/{id}` | **admin** | Look at the queue. |
| `GET /metrics` | **admin** | Numbers for monitoring. |

"service" is the token my website's adapter holds. "admin" is mine. The admin token is
accepted everywhere; the service token is refused on admin endpoints with 403.

## 2. Ordering a simulation

```
POST /v1/simulations                      202 Accepted
Idempotency-Key: <portfolio job id>       Location: /v1/simulations/0193b6f4-...
{ "capital": 10000,                       Retry-After: 2
  "risk_level": "medium",                 { "id": "0193b6f4-...", "status": "queued", ... }
  "time_span_years": 10,
  "industries": ["healthcare"] }

GET /v1/simulations/0193b6f4-...          200 OK
                                          { "status": "running", "progress": 0.6, ... }

GET /v1/simulations/0193b6f4-...          200 OK
                                          ETag: "sim-0193b6f4-v412"
                                          { "status": "succeeded", "result": { ... } }
```

Only three inputs are required. The others get defaults, and the answer always echoes the
values that were really used (strategy, rebalance, benchmark, seed).

**When no new work is created:**

1. Same `Idempotency-Key` as before: the first simulation comes back (200). If the key is
   reused with *different* inputs, that is a bug in the caller: 409.
2. Same inputs, same `data_version`, same seed as an existing simulation: that one comes
   back (200). This is the result cache.

**How long to poll.** `Retry-After` says how many seconds to wait. A simulation should
finish within 20 seconds on the VM. The adapter gives up after about 100 seconds and sends
`DELETE`.

## 3. Errors

Every error has the same JSON shape (the "problem details" standard, RFC 9457) plus a stable
`code` that programs can check:

```json
{ "type": "about:blank", "title": "Validation failed", "status": 422,
  "code": "validation_failed", "detail": "1 field is invalid.",
  "errors": [{ "field": "time_span_years", "message": "must be between 1 and 20" }] }
```

| Status | `code` | Meaning | What the caller should do |
|---|---|---|---|
| 401 | `unauthorized` | No token or a wrong one. | Fix configuration. Do not retry. |
| 403 | `forbidden` | Service token on an admin endpoint. | Do not retry. |
| 404 | `not_found` | No such simulation, ticker or job. | Do not retry. |
| 409 | `idempotency_conflict` | Key reused with other inputs. | Bug in the caller. |
| 422 | `validation_failed` | Input breaks a rule of the contract. | Show the message to the user. |
| 429 | `rate_limited` | Too many requests. | Wait `Retry-After`, then retry. |
| 503 | `queue_full`, `database_unavailable` | Temporarily cannot take work. | Wait `Retry-After`, then retry. |
| 500 | `internal_error` | My bug. | Retry once, then give up. |

Two different kinds of failure, and they must not be mixed up:

- The **request** failed: an HTTP error status, as above.
- The request was fine but the **simulation** failed: HTTP 200, `status: "failed"`, and an
  `error` object with its own code (`universe_too_small`, `not_enough_history`,
  `data_unavailable`, ...) and a `retryable` flag.

## 4. Rate limiting

- 120 requests a minute per token, 20 `POST /v1/simulations` a minute.
- At most 50 simulations waiting in the queue. More gets 503 `queue_full`. This protects
  the small server: refusing early is better than accepting work it cannot finish.
- Every answer carries `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset`.
  A 429 also carries `Retry-After`.
- v1 implementation: a token bucket (a counter that refills at a steady rate) in the API
  process's memory. Good enough for one API process. If I ever run two, the counter must
  move to Postgres or Redis. That is a possible bottleneck-loop story.

The real protection against the public is still the portfolio website (quotas, IP limits).
This limit protects the simulator from a bug in the adapter, for example a poll loop
without a pause.

## 5. Caching headers

| Endpoint | `Cache-Control` | `ETag` built from |
|---|---|---|
| Simulation, finished | `private, max-age=86400, immutable` | id + `data_version` |
| Simulation, not finished | `no-store` | none |
| Options, instruments | `private, max-age=3600` | `data_version` |
| Prices | `private, max-age=300` | ticker + range + `data_version` |
| Model portfolios, snapshot | `private, max-age=300` | `as_of` |

How `ETag` works: the caller remembers the fingerprint and sends it back as
`If-None-Match`. If nothing changed, the API answers `304 Not Modified` with no body. The
important part: the API can decide that **without running the big query**, because the
fingerprint is built from `data_version`, which is one tiny lookup.

The single invalidation rule for the whole system: **new data, new `data_version`, new
fingerprint**. Nothing has to be deleted from any cache by hand.

## 6. The daily snapshot

`GET /v1/snapshot/latest` returns the `Snapshot` shape. The `export_snapshot` job sends the
same document to Supabase by calling one database function there:

```sql
select sim.publish_snapshot(:payload::jsonb);
```

The simulator connects to Supabase as the role `sim_publisher`, which may call this
function and nothing else. The function stores the document under its `as_of` date in the
public table `sim_snapshots` and keeps the newest 30 days. Publishing the same day twice
replaces that day, so the job is safe to run again.

Rules that keep the snapshot small (under 256 KB, checked on both sides):

- At most 400 points per series. Under 400 trading days: every day. Longer: weekly, later
  monthly. Always keep the first point, the last point, the highest and the lowest.
- At most 25 positions per portfolio. Smaller ones are summed into one "Other" row.
- The outlook has one point per month.
- `schema_version` is 1. If I ever remove a field or change its meaning, it becomes 2, and
  the website shows "no data" for versions it does not know instead of a broken chart.

## 7. Mapping to the portfolio's Result

The adapter in the portfolio repo turns a simulation result into the website's generic
`Result` (`summary`, `series`, `tables`). The website's limits: 12 summary entries, 8 series
of at most 2,000 points, 4 tables of at most 500 rows and 12 columns.

| Result part | Filled from |
|---|---|
| `summary` | `metrics.portfolio`: final value, total return, CAGR, volatility, Sharpe, max drawdown. `metrics.benchmark`: final value, CAGR. Percent values multiplied by 100. |
| `series[0]` "Portfolio" | `series.dates` and `series.portfolio`, x = months since the first date |
| `series[1]` "SPY (benchmark)" | `series.dates` and `series.benchmark`, same x |
| `tables[0]` Allocation | `allocation`: ticker, name, sector, weight, amount |
| `tables[1]` Yearly returns | `yearly_returns` |
| `tables[2]` Range of outcomes | `outlook`: one row per listed month, columns p5 to p95 |
| `tables[3]` Notes | `warnings` plus `outlook.note` |

I write this mapping myself in milestone M5. The website's sample data already follows it,
so I can compare my output with what the page expects.

## 8. Admin jobs

`POST /v1/admin/jobs` with a `kind` and `args`:

| `kind` | `args` | What happens |
|---|---|---|
| `ingest_prices` | `since` (date, optional), `provider` (optional), `tickers` (list, optional) | Fetch missing days for the universe or the given tickers. |
| `ingest_fundamentals` | `tickers` (optional) | Fetch company facts and filing dates from EDGAR. |
| `update_model_portfolios` | `day` (optional, default: last trading day) | Value the three portfolios for that day. |
| `export_snapshot` | none | Build the snapshot and publish it. |
| `admin_command` | `command`, `params` | Reserved for later admin pages. Refused with 422 in v1. |

The `sim` CLI creates exactly these jobs. So there is one code path, whether I type a
command over SSH now or click a button on an admin page later.

## 9. Keeping code and contract the same

FastAPI builds its own OpenAPI description from my code (`app.openapi()`). A test compares
it with `docs/openapi.yaml`:

1. Load both.
2. For every path and method in the contract: it exists in the app, with the same
   parameters, the same status codes, and the same request and response schemas.
3. The app has no path that is missing from the contract.
4. Every `example` in the contract validates against its schema.

What the test ignores: descriptions, summaries, examples' wording and the order of keys.

The test runs in GitHub Actions on every push. So there are only two ways to change the API,
and both are visible in a diff: change the contract first and make the code follow, or the
build goes red.

When I change the contract's examples, I also re-run the mock generator in the portfolio
repo (`web/scripts/gen-sim-mock.mjs`), so the website's sample data follows.

## 10. Versioning

All paths start with `/v1`. Adding a field is allowed any time. Removing a field, renaming
one, or changing its meaning needs `/v2` (or `schema_version` 2 for the snapshot). With one
caller that I also control this sounds strict, but practising it is the point.
