# Overview

## The idea

I give the tool four things:

- an amount of money,
- a risk level (low, medium or high),
- a time span,
- and, if I want, some industries or themes I care about (Healthcare, Defense, AI).

It then picks US stocks and ETFs (funds that hold many stocks and trade like one), decides
how much goes into each, and shows two things: how that portfolio would have done in the
past, and how it is doing now. Both are compared with the laziest sensible choice: buying
one S&P 500 fund (SPY) and doing nothing.

It is a simulator. No real money moves, ever. It is not a trading bot and not advice.

## Why I am building it

The real point is the engineering, not the finance.

A friend at a startup told me that most student CVs sound good but fall apart at questions
like: "Your server has 2 GB of RAM and many users send requests that need big table joins.
How do you keep it fast?"

So this project creates those problems on purpose. I give the database too little memory
and a lot of data. I depend on outside services that fail. Then I solve each problem,
measure the difference, and write it down. Each one becomes a story I can tell with numbers.

## Goals

1. A working backend I wrote myself: API, background worker, database, command line tool.
2. Real problems, each solved and measured:

| # | Problem | What I will be able to show |
|---|---|---|
| 1 | Small server, big data | Postgres with 2 GB RAM and about 25 million price rows. Indexes, query plans, partitioning, connection pooling. |
| 2 | Unreliable outside APIs | Rate limits, retries with backoff, downloads that are safe to run twice, swappable data sources. |
| 3 | Slow work outside the request | A job queue. The caller gets a job id, the result appears when ready. |
| 4 | Data correctness | Splits and dividends, missing days, look-ahead bias, survivorship bias. |
| 5 | Reproducibility | Same inputs + same data = same result, including seeded random numbers. |
| 6 | Caching | Many requests for the same popular stocks, and knowing when a cached answer is stale. |
| 7 | Security | A public site with no open port on the server: rate limits per IP, validated input, a proper admin login, security headers. Only I can change things. |
| 8 | Observability | Logs, metrics, p50/p95 latency, slow-query tracking. A number behind every claim. |
| 9 | Extensibility | A plugin system, so new data sources and strategies are one new file. |

3. Three live model portfolios (low, medium, high risk) that start on a fixed day and are
   valued every day. This is a forward test: visitors see what really happened after the
   start, not only a backtest that could have been tuned to look good.
4. After the first version works, a "bottleneck loop": load test, measure, find the slowest
   part, fix one thing, measure again, write a short before/after note in `BENCHMARKS.md`.

## Non-goals

- **Beating the market.** The picking rules are simple and explainable. If they beat SPY, good.
  If not, the dashboard says so honestly.
- **A quant project.** No machine learning, no factor models, no intraday data.
- **A product with user accounts.** Anyone can look and run a simulation. Nobody registers.
  One admin: me.
- **A JavaScript app.** The pages are plain HTML rendered by the backend (Jinja2 templates
  and HTMX). The backend stays the centre of the project.
- **Real trading, real money, or advice.** Never.
- **Europe, Trading 212 import, news sentiment.** Later, as plugins.
- **Part of my portfolio website.** It is its own app with its own address. The portfolio
  may link to it later.

## The engineering story in plain words

Someone opens the site and fills in the form. The server checks the input and writes a job
into a table. It answers right away with the address of a result page. A worker process
picks the job up, loads prices from a Postgres database that is deliberately too small to be
comfortable, runs the numbers, and saves the result. The page asks again every two seconds
and shows the result when it is there.

Every night the worker downloads new prices from a free source that only allows about 50
requests an hour, so it has to be patient, careful and able to continue where it stopped.
Then it values the three model portfolios and builds one small summary for the dashboard.

The site is public, but the server has no open ports. It only ever makes outgoing
connections, one of them a tunnel to Cloudflare that visitors' requests travel back through.

When this works, I make it hurt: many requests at once, all 25 million rows, 2 GB of memory.
I find what breaks first, fix exactly that, and write down the numbers.

## What is where

| File | What it answers |
|---|---|
| `01-before-you-start.md` | What do I need to know and set up first? |
| `02-architecture.md` | What are the parts and why are they shaped this way? |
| `03-data-model.md` | Which tables, keys and indexes, and how big do they get? |
| `openapi.yaml`, `04-api.md` | What exactly do the API and the pages accept and return? |
| `05-analysis.md` | How is every number calculated and how do I test it? |
| `06-plugins.md` | How do I add a data source or a strategy? |
| `07-roadmap.md` | What do I build, in which order, one session at a time? |

## Disclaimer

This is a learning project. Nothing here is financial advice. Past results, simulated or
real, say little about the future.
