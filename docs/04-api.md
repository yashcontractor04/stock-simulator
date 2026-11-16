# API and pages

`openapi.yaml` is the exact contract for the JSON API. This file is the readable companion:
what the endpoints and pages are for, how the pieces behave, and how I keep code and
contract the same.

To look at the contract nicely: paste `openapi.yaml` into
[editor.swagger.io](https://editor.swagger.io/), or later open `/docs` on the running API.

## 1. Everything the server answers

### Pages (HTML)

Rendered with Jinja2 templates. Not part of `openapi.yaml`, because they return HTML, not
JSON. They get their data from the same service functions as the JSON endpoints next to
them.

| Page | Method and address | Who | Same data as |
|---|---|---|---|
| Dashboard | `GET /` | public | `GET /v1/snapshot/latest` |
| Simulation form | `GET /simulate` | public | `GET /v1/meta/options` |
| Submit the form | `POST /simulate` | public, rate-limited | `POST /v1/simulations` |
| One simulation | `GET /simulations/{id}` | public | `GET /v1/simulations/{id}` |
| Progress piece (HTMX polls it) | `GET /simulations/{id}/status` | public | `GET /v1/simulations/{id}` |
| About | `GET /about` | public | none |
| Login form | `GET /admin/login`, `POST /admin/login` | public, rate-limited | none |
| Logout | `POST /admin/logout` | admin | none |
| Data status | `GET /admin` | admin | `GET /v1/admin/status` |
| Jobs | `GET /admin/jobs`, `POST /admin/jobs` | admin | `/v1/admin/jobs` |
| Settings | `GET /admin/settings`, `POST /admin/settings` | admin | `/v1/admin/settings` |
| Static files | `GET /static/...` | public | none |

`POST /simulate` answers with a redirect to `/simulations/{id}` (the "post, redirect, get"
pattern: after a form post the browser lands on a normal page, so reloading does not send
the form again).

### JSON API

| Endpoint | Who | What |
|---|---|---|
| `GET /healthz` | public | The process runs. |
| `GET /readyz` | public | The database answers. Shows `data_version`. |
| `GET /v1/meta/options` | public | Risk levels, industries, themes, limits. |
| `POST /v1/simulations` | public, rate-limited | Order a simulation. Answers 202 with an id. |
| `GET /v1/simulations/{id}` | public | Status, and the result when ready. |
| `DELETE /v1/simulations/{id}` | public | Cancel. |
| `GET /v1/model-portfolios` | public | The three live portfolios, short form. |
| `GET /v1/snapshot/latest` | public | The daily snapshot. Also read by the README workflow. |
| `GET /v1/instruments` | public | Search stocks and ETFs. |
| `GET /v1/instruments/{ticker}/prices` | **admin** for now | Daily prices of one instrument. |
| `GET /v1/admin/status` | **admin** | Data and system state. |
| `GET`, `PATCH /v1/admin/settings` | **admin** | Limits and the on/off switch. |
| `POST /v1/admin/jobs` | **admin** | Queue ingestion, model update, snapshot build. |
| `GET /v1/admin/jobs`, `GET /v1/admin/jobs/{id}` | **admin** | Look at the queue. |
| `GET /metrics` | **admin** | Numbers for monitoring. |

"public" means no account and no token. "admin" means the request carries my session cookie
from the login. Why prices are admin-only for now: see decision D5 in `02-architecture.md`.

## 2. Ordering a simulation

```
POST /v1/simulations                      202 Accepted
Idempotency-Key: 7c1e...                  Location: /v1/simulations/0193b6f4-...
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

1. Same `Idempotency-Key` as before: the first simulation comes back (200). The form puts a
   random key into a hidden field, so a double click creates one job. If a key is reused
   with *different* inputs: 409.
2. Same inputs, same `data_version`, same seed as an existing simulation: that one comes
   back (200). This is the result cache. On a public site it matters a lot: a hundred
   visitors pressing "run" with the default values cause one computation.

**In the browser.** The result page includes a small piece that HTMX reloads every two
seconds from `/simulations/{id}/status`. While the job runs, the piece shows the progress.
When it is done, the server sends the full result instead, without the polling attribute, so
the polling stops by itself. If JavaScript is off, the page shows a "reload" link.

## 3. Errors

Every JSON error has the same shape (the "problem details" standard, RFC 9457) plus a stable
`code` that programs can check:

```json
{ "type": "about:blank", "title": "Validation failed", "status": 422,
  "code": "validation_failed", "detail": "1 field is invalid.",
  "errors": [{ "field": "time_span_years", "message": "must be between 1 and 20" }] }
```

| Status | `code` | Meaning | What the caller should do |
|---|---|---|---|
| 401 | `unauthorized` | Admin endpoint without a valid session. | Log in. |
| 403 | `csrf_failed` | Admin change without the CSRF token. | Reload the page. |
| 404 | `not_found` | No such simulation, ticker or job. | Do not retry. |
| 409 | `idempotency_conflict` | Key reused with other inputs. | Bug in the caller. |
| 422 | `validation_failed` | Input breaks a rule of the contract. | Show the message next to the field. |
| 429 | `rate_limited` | Too many requests from this IP address. | Wait `Retry-After`, then retry. |
| 503 | `queue_full`, `simulations_disabled`, `database_unavailable` | Temporarily cannot take work. | Wait `Retry-After`, then retry. |
| 500 | `internal_error` | My bug. | Retry once, then give up. |

Pages show the same errors as HTML: a 422 re-renders the form with the messages, a 429 or
503 shows a short notice with the waiting time, a 404 and a 500 have their own plain pages.
An error page never shows a stack trace or an internal address.

Two different kinds of failure, and they must not be mixed up:

- The **request** failed: an HTTP error status, as above.
- The request was fine but the **simulation** failed: HTTP 200, `status: "failed"`, and an
  `error` object with its own code (`universe_too_small`, `not_enough_history`,
  `data_unavailable`, ...) and a `retryable` flag.

## 4. Rate limiting

Limits are per IP address, because there are no accounts.

| What | Limit | Changeable on the settings page |
|---|---|---|
| Any request | 120 a minute | yes |
| New simulations | 5 per 10 minutes and 30 a day | yes |
| Waiting simulations, all visitors together | 50, then 503 `queue_full` | yes |
| Login attempts | 5 per 15 minutes | no |

- Every JSON answer carries `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset`.
  A 429 also carries `Retry-After`.
- **Which IP address?** Locally, the address of the connection. Behind the tunnel, the
  `CF-Connecting-IP` header that Cloudflare sets, and only if `SIM_TRUST_PROXY=cloudflare`.
  Trusting that header without the tunnel would let anyone pick their own address.
- **Privacy.** The limiter keeps a keyed hash (HMAC with a secret) of the address, not the
  address, and forgets it after a day.
- v1 implementation: a token bucket (a counter that refills at a steady rate) per hashed
  address in the API process's memory, with a cap on how many addresses it remembers. Good
  enough for one API process. If I ever run two, the counters must move to Postgres or
  Redis. That is a possible bottleneck-loop story.
- The queue limit protects the small server: refusing early is better than accepting work it
  cannot finish.

## 5. Caching headers

| Endpoint or page | `Cache-Control` | `ETag` built from |
|---|---|---|
| Simulation, finished | `public, max-age=86400, immutable` | id + `data_version` |
| Simulation, not finished; progress piece; the form | `no-store` | none |
| Options, instruments | `public, max-age=3600` | `data_version` |
| Dashboard, snapshot, model portfolios | `public, max-age=300` | `as_of` |
| Prices | `private, max-age=300` | ticker + range + `data_version` |
| Everything under `/admin` and `/v1/admin` | `no-store` | none |
| Static files with a version in the name | `public, max-age=31536000, immutable` | none |

`public` means shared caches may keep the answer too. Behind the tunnel that is Cloudflare:
the dashboard is then served from Cloudflare's cache for five minutes, and my VM is not
asked at all. That is the cheapest speed-up there is.

How `ETag` works: the caller remembers the fingerprint and sends it back as
`If-None-Match`. If nothing changed, the API answers `304 Not Modified` with no body. The
important part: the API can decide that **without running the big query**, because the
fingerprint is built from `data_version`, which is one tiny lookup.

The single invalidation rule for the whole system: **new data, new `data_version`, new
fingerprint**. Nothing has to be deleted from any cache by hand.

One trap to avoid: a page that contains a CSRF token or anything per-visitor must never be
`public`. Public pages therefore contain no tokens. The simulation form needs none, because
it changes nothing that belongs to a user.

## 6. The daily snapshot

`GET /v1/snapshot/latest` returns the `Snapshot` shape: the three model portfolios with
performance, allocation and outlook, in one small document. The `build_snapshot` job
writes it into the `snapshots` table once a day. Three things read it:

1. the dashboard page,
2. the GitHub Action that refreshes the README table,
3. later, maybe, a summary card on my portfolio website.

Rules that keep it small (under 256 KB):

- At most 400 points per series. Under 400 trading days: every day. Longer: weekly, later
  monthly. Always keep the first point, the last point, the highest and the lowest.
- At most 25 positions per portfolio. Smaller ones are summed into one "Other" row.
- The outlook has one point per month.
- `schema_version` is 1. If I ever remove a field or change its meaning, it becomes 2, and
  readers that do not know that version should refuse it instead of showing wrong numbers.

Building it once a day, instead of on every page view, means the most visited page costs one
primary-key read.

## 7. Admin jobs

`POST /v1/admin/jobs` (or the form on `/admin/jobs`) with a `kind` and `args`:

| `kind` | `args` | What happens |
|---|---|---|
| `ingest_prices` | `since` (date, optional), `provider` (optional), `tickers` (list, optional) | Fetch missing days for the universe or the given tickers. |
| `ingest_fundamentals` | `tickers` (optional) | Fetch company facts and filing dates from EDGAR. |
| `update_model_portfolios` | `day` (optional, default: last trading day) | Value the three portfolios for that day. |
| `build_snapshot` | none | Build and store the snapshot. |

The `sim` CLI creates exactly these jobs. So there is one code path, whether I type a
command over SSH or click a button on the admin page.

## 8. Keeping code and contract the same

FastAPI builds its own OpenAPI description from my code (`app.openapi()`). A test compares
it with `docs/openapi.yaml`:

1. Load both.
2. For every path and method in the contract: it exists in the app, with the same
   parameters, the same status codes, and the same request and response schemas.
3. The app has no JSON path that is missing from the contract. (Page routes are registered
   with `include_in_schema=False`, so they do not appear.)
4. Every `example` in the contract validates against its schema.

What the test ignores: descriptions, summaries, examples' wording and the order of keys.

The test runs in GitHub Actions on every push. So there are only two ways to change the API,
and both are visible in a diff: change the contract first and make the code follow, or the
build goes red.

The templates' sample data (`web/preview/`) is generated from the contract's examples. When
I change an example, I re-run the generator, so the page preview follows.

A second test for the pages: every page route renders without error from the sample data,
and every route under `/admin` and `/v1/admin` answers 401 or a redirect to the login
without a session.

## 9. Versioning

All JSON paths start with `/v1`. Adding a field is allowed any time. Removing a field,
renaming one, or changing its meaning needs `/v2` (or `schema_version` 2 for the snapshot).
The README workflow is an outside reader of the snapshot, so this is not only practice.
