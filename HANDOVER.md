# Handover

For whoever helps next, human or AI. Read `CLAUDE.md` first: Yash writes the backend,
helpers explain, review and write docs. The web pages are the one exception.

Last updated: 2026-11-16 (evening).

## Where things stand

**Docs are complete. The web pages exist on sample data. No backend code exists yet.**
Yash starts building after his foundations phase ends in mid-December 2026.

### The big change on 2026-11-16

The simulator is now a **standalone web app** with its own pages and its own public
address. The earlier plan (reached only through the portfolio website's job queue, with a
snapshot pushed to the portfolio's Supabase) is dropped. Gone from the docs: the portfolio
adapter, the "service" token, publishing to Supabase. New: Jinja2 + HTMX pages, public
access limited per IP address, an admin login, Cloudflare Tunnel. The reasoning is decision
D13 in `docs/02-architecture.md`.

### Docs (written with Fable, for Yash to review)

| File | State |
|---|---|
| `docs/00-overview.md` | written, updated for the standalone app |
| `docs/01-before-you-start.md` | written. Has unchecked boxes for terms Yash must read himself |
| `docs/02-architecture.md` | rewritten: sections 1, 2, 3, 5, 6 (web interface, tunnel setup), 8 (security), 13 decisions |
| `docs/03-data-model.md` | written. SQL is sketches, not final migrations. New section 6a (admin tables) |
| `docs/openapi.yaml` | valid OpenAPI 3.1, every example checked against its schema. Public by default, admin by session cookie |
| `docs/04-api.md` | rewritten: page routes, per-IP limits, public caching |
| `docs/05-analysis.md` | written. Each method has a known-answer example for a test |
| `docs/06-plugins.md` | written |
| `docs/07-roadmap.md` | 29 steps. M5 and M6.1 rewritten, new step 6.5 (public address) |
| `README.md` | skeleton with TODO markers and a sample-data screenshot |
| `LEARNING.md`, `BENCHMARKS.md` | templates |

### Frontend, built by Fable

Everything in `src/sim/web/`. Yash did not write these files and should not present them as
his own. Details and the list of what each template expects: `src/sim/web/README.md`.

| What | Files | State |
|---|---|---|
| Page templates | `templates/base.html`, `dashboard.html`, `simulate.html`, `simulation.html`, `_simulation_status.html`, `_parts.html`, `about.html`, `error.html` | done, on sample data |
| Admin templates | `templates/admin/login.html`, `status.html`, `jobs.html`, `settings.html` | done, on sample data |
| Styles | `static/css/tokens.css` (copied from the portfolio), `static/css/app.css` | done |
| Scripts | `static/js/htmx-2.0.11.min.js` (third party), `static/js/app.js` | done |
| Fonts | `static/fonts/` Inter and JetBrains Mono with licences | done |
| Helpers | `templating.py`, `filters.py`, `charts.py` | done, pass ruff |
| Preview | `preview/serve.py` (stand-in server), `preview/mock.py` (sample data from `openapi.yaml`) | done |

Checked in a browser at desktop and phone width: every page renders, no horizontal
scrolling, no Content-Security-Policy violations, the result page polls and stops by itself.
Not checked: screen reader output, browsers other than Chrome.

What is **not** there and is Yash's to write (roadmap M5): the FastAPI routes that render
these templates, form handling, the login and sessions, CSRF checks, rate limits, security
headers.

### Open: for Yash

- [ ] Read `docs/02-architecture.md` sections 6 and 8 and say if anything is unclear or wrong.
- [ ] Look at the pages: `cd src && python -m sim.web.preview.serve`.
- [ ] Create a Tiingo account and read its terms for the free plan. This matters more now
      that the site is public (`02-architecture.md`, decision D5). The raw prices endpoint
      stays admin-only until that is settled.
- [ ] Decide the model portfolios' start date before looking at any results (roadmap 5.1).
- [ ] Get a domain when convenient (GitHub Student Developer Pack). Only step 6.5 needs it.
- [ ] Before the public address goes live: decide on Impressum and privacy notice.
- [ ] Start at roadmap step 1.1 after the foundations phase.

### Open: the portfolio repo

Nothing in this repo depends on it any more. But `yashcontractor04/portfolio` still has
**pull request #1** (branch `stock-sim-frontend`) from the earlier plan: a Dashboard tab on
sample data, a Supabase migration for a snapshot table, an adapter skeleton, and docs that
describe the old setup. It was left untouched on Yash's instruction. It no longer matches
this plan and should be closed or reworked, not merged as it is. In particular, do not
apply its migration. Yash decides what happens there.

### Open: things an assistant could still improve

- Video recommendations in the roadmap are channel + title to search for, not links. They
  were not verified one by one.
- Stooq as the source for the 25 million row load (roadmap 6.3) is a plan, not a verified
  fact. Its terms, and whether its prices are raw or adjusted, need checking before M6.
- Tiingo's free limits (about 50 requests an hour, 1,000 a day) were looked up in November
  2026. Check again before M1.
- The Cloudflare setup steps describe the dashboard as known in 2026. Menu names move.
  Check against Cloudflare's docs when doing step 6.5.
- The core ETF list, the sector mapping from SIC codes and the theme lists are described
  but not written out.
- `.env.example` and `pyproject.toml` do not exist yet. They belong to roadmap step 1.1.
  Until then `src/sim/web/` is run from the `src/` folder.

## Decisions already made (do not reopen without asking Yash)

- Standalone app. Own pages with Jinja2 + HTMX, no React. English only for now.
- Public = view and run simulations, limited per IP address, no accounts.
- Admin = one password login with server-side sessions; Cloudflare Access added in front
  once the tunnel exists.
- Public address through Cloudflare Tunnel once there is a domain. No inbound ports.
- Benchmark: SPY. Start with about 500 tickers; the full 5,000 come in M6.
- Plain SQL with psycopg 3, no ORM. Job queue in a Postgres table.
- Raw prices plus a corporate actions table.
- All of `docs/02-architecture.md` section 10.

## How things stay in sync

`docs/openapi.yaml` is the source of truth. Three things follow it:

1. The FastAPI code (a CI test will compare them, roadmap 4.4).
2. The templates: they receive the contract's shapes as dictionaries.
3. The sample data: built at start-up from the contract's examples by
   `src/sim/web/preview/mock.py`. Nothing is copied, so it cannot go stale.

When the contract changes: change it first, run `python3` with a validator over it (every
example must match its schema), then open the preview and check the pages still render.

## Style to keep

Short plain sentences, first person, terms explained in brackets the first time, no hype.
Math in LaTeX, never in code formatting. Mermaid for diagrams. No AI attribution in commits
or pull requests. Full rules in `CLAUDE.md`.

## How to help in a session

1. Read `LEARNING.md` to see where Yash really is and what confused him last time.
2. Find his step in `docs/07-roadmap.md`.
3. Explain, review, ask. Do not implement backend code.
4. At the end: what you did, what he should check, what is next. Update this file if the
   state changed.
