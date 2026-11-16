# The web pages

**Frontend, built by Fable** (an AI model), not by me. I asked for it so I can
spend my time on the backend. Everything in this folder is fair game for an assistant to
change. Everything outside it is mine to write.

The pages run on **sample data** until the backend exists. The sample data is built from
the examples in `docs/openapi.yaml`, so the pages already expect the real shapes.

## Look at them now

```bash
pip install jinja2 pyyaml
cd src
python -m sim.web.preview.serve
```

Then open http://localhost:8001. The list of pages and special cases (empty dashboard, form
with errors, a failed simulation, error pages) is at the top of `preview/serve.py`.

The preview server is a stand-in. It has no database and fakes a simulation moving from
"queued" to "finished" in a few seconds. It is not the backend and will be deleted or kept
only for tests once the real routes exist.

## What is here

| File | What it is |
|---|---|
| `templates/base.html` | The frame around every page: header, the window, footer. |
| `templates/dashboard.html` | The three model portfolios. |
| `templates/simulate.html` | The form. |
| `templates/simulation.html` | One simulation. Includes the piece below. |
| `templates/_simulation_status.html` | The part that changes: progress, then the result. HTMX reloads it every 2 seconds until the job is done. |
| `templates/_parts.html` | Shared pieces: the two charts, the allocation table, warnings. |
| `templates/about.html`, `error.html` | Plain pages. |
| `templates/admin/*.html` | Login, data status, jobs, settings. |
| `static/css/tokens.css` | Colours, radii, fonts. Copied from my portfolio site so both look the same. |
| `static/css/app.css` | All other styles. Plain CSS, no build step. |
| `static/js/htmx-2.0.11.min.js` | HTMX, kept in the repo so the page loads nothing from other sites. |
| `static/js/app.js` | Ten lines: sends the CSRF token with HTMX requests on admin pages. |
| `static/fonts/` | Inter and JetBrains Mono, with their licences. |
| `templating.py` | Builds the Jinja2 environment (filters, chart helpers, autoescape on). |
| `filters.py` | How money, percentages and dates are written. |
| `charts.py` | Turns series into SVG coordinates. Pure functions. |
| `preview/` | The stand-in server and the sample data builder. |

## What each template expects

This is the interface between my backend and the pages. A page route collects these values
and renders the template. The shapes are the ones from `docs/openapi.yaml`, as plain
dictionaries (for a pydantic model: `model.model_dump(mode="json")`).

Every page: `nav` (which menu entry is current: `dashboard`, `simulate`, `about`,
`admin-status`, `admin-jobs`, `admin-settings` or an empty string). Optional: `sample`
(true shows the "SAMPLE DATA" badge; leave it out once the data is real), `admin` (true
when logged in) and, on admin pages, `csrf_token`.

| Template | Route | Extra values |
|---|---|---|
| `dashboard.html` | `GET /` | `snapshot` (`Snapshot` or `None`), `selected` (`low`, `medium` or `high`, from `?risk=`, default `medium`) |
| `simulate.html` | `GET /simulate`, and `POST /simulate` when the input is wrong | `options` (`Options`), `values` (what to pre-fill: `capital`, `risk_level`, `time_span_years`, `industries`, `themes`), `errors` (field name to message; `_form` for a general one), `enabled` (the settings switch), `idempotency_key` (a fresh random string) |
| `simulation.html` | `GET /simulations/{id}` | `simulation` (`Simulation`) |
| `_simulation_status.html` | `GET /simulations/{id}/status` | `simulation` |
| `about.html` | `GET /about` | none |
| `error.html` | error handlers | `status_code`, `title`, `detail`, `retry_after` (seconds or `None`) |
| `admin/login.html` | `GET /admin/login` | `error` (message or `None`), `locked` (true after too many attempts) |
| `admin/status.html` | `GET /admin` | `status` (`AdminStatus`) |
| `admin/jobs.html` | `GET /admin/jobs` | `jobs` (list of `Job`), `kinds` (job kinds that may be started) |
| `admin/settings.html` | `GET /admin/settings` | `settings` (`Settings`), `errors`, `saved` (true right after saving) |

Forms post these fields:

| Form | Fields |
|---|---|
| `POST /simulate` | `capital`, `risk_level`, `time_span_years`, `industries` (repeated), `themes` (repeated), `idempotency_key` |
| `POST /admin/login` | `password` |
| `POST /admin/logout` | `csrf_token` |
| `POST /admin/jobs` | `csrf_token`, `kind` |
| `POST /admin/settings` | `csrf_token`, `public_simulations_enabled` (`true` or `false`), and the four number fields named like in `Settings` |

A missing value is an error on purpose (`StrictUndefined`): a page should fail loudly in a
test, not show an empty spot to a visitor.

## Rules the templates follow

- **No inline scripts and no inline styles.** The Content-Security-Policy in
  `docs/02-architecture.md` forbids them. Widths and colours in charts are SVG attributes
  and CSS classes. The preview server sends the same policy, so a violation shows up in the
  browser console there first.
- **Autoescape is always on.** Never use the `safe` filter.
- **Works without JavaScript.** The portfolio cards are normal links and the form is a
  normal form. HTMX only makes them smoother.
- **Public pages contain nothing per visitor** (no tokens), so they can be cached.
- **Keyboard and screen readers:** a skip link, visible focus, labels on every field, a text
  summary on every chart, tables with header cells.
- Green and red mean gain and loss and nothing else.

## Not done yet

- Hover values on the charts (would need a little JavaScript).
- Impressum and the Cloudflare note on the about page (roadmap step 6.5, my decision).
- Warning texts come from the API as English sentences. Fine while the site is English only.
- No automated test here yet. Roadmap step 5.3 adds one that renders every page from the
  sample data.
