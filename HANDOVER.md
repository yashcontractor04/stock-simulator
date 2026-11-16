# Handover

For whoever helps next, human or AI. Read `CLAUDE.md` first: Yash writes the code, helpers
explain, review and write docs.

Last updated: 2026-11-16.

## Where things stand

**This repo has docs only. No code exists yet.** That is intended. Yash starts building
after his foundations phase ends in mid-December 2026.

### Done

| File | State |
|---|---|
| `docs/00-overview.md` | written |
| `docs/01-before-you-start.md` | written. Has unchecked boxes for terms Yash must read himself |
| `docs/02-architecture.md` | written. 10 decisions in ADR style, RAM/CPU budget |
| `docs/03-data-model.md` | written. SQL is sketches, not final migrations |
| `docs/openapi.yaml` | written and validated (OpenAPI 3.1, every example checked against its schema) |
| `docs/04-api.md` | written |
| `docs/05-analysis.md` | written. Each method has a known-answer example for a test |
| `docs/06-plugins.md` | written |
| `docs/07-roadmap.md` | written. 27 steps in 6 milestones, plus bottleneck loops |
| `README.md` | skeleton with TODO markers |
| `LEARNING.md`, `BENCHMARKS.md` | templates |
| `CLAUDE.md` | instructions for assistants |

In the **portfolio** repo (`yashcontractor04/portfolio`), pull request #1, branch
`stock-sim-frontend`: the Dashboard tab and demo run on sample data, the Supabase migration
for `sim_snapshots`, the adapter skeleton, updated docs. See that repo's
`docs/ARCHITECTURE.md` section 4a and `docs/ROADMAP.md` item 19.

### Open: for Yash

- [ ] Review and merge portfolio PR #1, then apply the migration and the runner seed in the
      Supabase SQL editor (listed in the PR).
- [ ] Create a Tiingo account and read its terms for the free plan (`01-before-you-start.md`).
- [ ] Decide the model portfolios' start date before looking at any results (roadmap 5.1).
- [ ] Start at roadmap step 1.1 after the foundations phase.

### Open: things an assistant could still improve in the docs

- Video recommendations in the roadmap are given as channel + title to search for, not as
  links, because they were not verified one by one. Checking them and adding links would help.
- Stooq as the source for the 25 million row load (roadmap 6.3) is a plan, not a verified
  fact. Its terms, and whether its prices are raw or adjusted, need checking before M6.
- Tiingo's free limits (about 50 requests an hour, 1,000 a day) were looked up in November
  2026. Check again before M1.
- The core ETF list, the sector mapping from SIC codes and the theme lists are described
  but not written out.
- A `.env.example` does not exist yet. It belongs to roadmap step 1.1.

## Decisions already made (do not reopen without asking Yash)

- Benchmark: SPY.
- Start with about 500 tickers; the full 5,000 come in M6.
- Plain SQL with psycopg 3, no ORM. Job queue in a Postgres table.
- Raw prices plus a corporate actions table.
- The simulator has no open ports. The website talks to it through the portfolio worker's
  adapter and reads a pushed daily snapshot.
- All of `docs/02-architecture.md` section 10.

## How the two repos stay in sync

`docs/openapi.yaml` here is the source of truth. Three things follow it:

1. This repo's FastAPI code (a CI test will compare them, roadmap 4.4).
2. `portfolio/web/src/lib/sim/schema.ts` (the snapshot shape, checked with zod).
3. `portfolio/web/src/lib/sim/mock/*.json`, generated from the examples by
   `portfolio/web/scripts/gen-sim-mock.mjs <path to openapi.yaml>`.

When the contract changes: update it here first, then re-run the generator and adjust the
schema in the portfolio repo, in one pull request there.

## Style to keep

Short plain sentences, first person, terms explained in brackets the first time, no hype.
Math in LaTeX, never in code formatting. Mermaid for diagrams. No AI attribution in commits
or pull requests. Full rules in `CLAUDE.md`.

## How to help in a session

1. Read `LEARNING.md` to see where Yash really is and what confused him last time.
2. Find his step in `docs/07-roadmap.md`.
3. Explain, review, ask. Do not implement.
4. At the end: what you did, what he should check, what is next. Update this file if the
   state changed.
