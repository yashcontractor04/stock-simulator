"""Sample data for the pages, built from the EXAMPLES in docs/openapi.yaml.

Frontend helper, built by Fable. The pages are designed against the API contract,
so the sample data must come from it too. The contract's examples only have a few
points per chart line; this module fills the gaps with a seeded random walk that
still passes through every example point. Same input, same output, every time.
"""

from __future__ import annotations

import copy
import datetime as dt
import math
import random
from pathlib import Path

import yaml

CONTRACT = Path(__file__).resolve().parents[4] / "docs" / "openapi.yaml"


def _example(
    spec: dict,
    path: str,
    method: str = "get",
    status: str = "200",
    name: str | None = None,
):
    content = spec["paths"][path][method]["responses"][status]["content"][
        "application/json"
    ]
    return content["examples"][name]["value"] if name else content["example"]


def _fill_dates(anchors: list[str], step: int) -> list[str]:
    first, last = dt.date.fromisoformat(anchors[0]), dt.date.fromisoformat(anchors[-1])
    days = set(anchors)
    day = first
    while day < last:
        shifted = day + dt.timedelta(
            days={5: 2, 6: 1}.get(day.weekday(), 0)
        )  # skip weekends
        if shifted <= last:
            days.add(shifted.isoformat())
        day += dt.timedelta(days=step)
    return sorted(days)


def _fill_values(anchor_dates, anchor_values, dates, rng, wiggle) -> list[float]:
    values: list[float] = []
    for i in range(len(anchor_dates) - 1):
        inside = [d for d in dates if anchor_dates[i] <= d < anchor_dates[i + 1]]
        a, b = math.log(anchor_values[i]), math.log(anchor_values[i + 1])
        walk = [0.0]
        for _ in inside:
            walk.append(walk[-1] + (rng.random() - 0.5) * wiggle)
        for k in range(len(inside)):
            part = k / len(inside)
            values.append(
                round(math.exp(a + (b - a) * part + walk[k] - walk[-1] * part), 2)
            )
    values.append(anchor_values[-1])
    return values


def expand_series(series: dict, step: int, seed: int) -> dict:
    dates = _fill_dates(series["dates"], step)
    scale = math.sqrt(step)
    return {
        "dates": dates,
        "portfolio": _fill_values(
            series["dates"],
            series["portfolio"],
            dates,
            random.Random(seed),
            0.016 * scale,
        ),
        "benchmark": _fill_values(
            series["dates"],
            series["benchmark"],
            dates,
            random.Random(seed),
            0.021 * scale,
        ),
    }


def expand_outlook(outlook: dict) -> dict:
    """One point per month instead of the few in the example."""
    anchors = outlook["months"]
    months = list(range(anchors[-1] + 1))

    def band(values: list[float]) -> list[float]:
        out = []
        for m in months:
            i = max(k for k, x in enumerate(anchors[:-1]) if x <= m)
            part = (m - anchors[i]) / (anchors[i + 1] - anchors[i])
            out.append(
                round(
                    math.exp(
                        math.log(values[i])
                        + (math.log(values[i + 1]) - math.log(values[i])) * part
                    ),
                    2,
                )
            )
        return out

    return {
        **outlook,
        "months": months,
        **{p: band(outlook[p]) for p in ("p5", "p25", "p50", "p75", "p95")},
    }


def load(contract: Path = CONTRACT) -> dict:
    """Everything the preview needs, keyed by what the templates call it."""
    spec = yaml.safe_load(contract.read_text())

    snapshot = copy.deepcopy(_example(spec, "/v1/snapshot/latest"))
    for i, portfolio in enumerate(snapshot["portfolios"]):
        portfolio["series"] = expand_series(portfolio["series"], 1, 11 + i)
        portfolio["outlook"] = expand_outlook(portfolio["outlook"])

    one = "/v1/simulations/{simulation_id}"
    done = copy.deepcopy(_example(spec, one, name="succeeded"))
    done["result"]["series"] = expand_series(done["result"]["series"], 10, 7)
    done["result"]["outlook"] = expand_outlook(done["result"]["outlook"])

    jobs = _example(spec, "/v1/admin/jobs")["items"]
    queued_job = _example(spec, "/v1/admin/jobs", method="post", status="202")
    return {
        "snapshot": snapshot,
        "options": _example(spec, "/v1/meta/options"),
        "simulation_queued": _example(
            spec, "/v1/simulations", method="post", status="202"
        ),
        "simulation_running": _example(spec, one, name="running"),
        "simulation_succeeded": done,
        "simulation_failed": _example(spec, one, name="failed"),
        "admin_status": _example(spec, "/v1/admin/status"),
        "settings": _example(spec, "/v1/admin/settings"),
        "jobs": [
            *jobs,
            {
                **queued_job,
                "id": "0193b702-aaaa-7a10-8f3b-6d1e9a4c2b78",
                "kind": "build_snapshot",
                "args": {},
            },
        ],
        "job_kinds": spec["components"]["schemas"]["AdminJobRequest"]["properties"][
            "kind"
        ]["enum"],
    }
