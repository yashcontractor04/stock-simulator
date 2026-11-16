"""Turns numbers into the coordinates the SVG charts in the templates need.

Frontend helper, built by Fable. Pure functions: no database, no network, no state.
The templates call these as Jinja globals (see templating.py).

All charts share one coordinate box: 1000 wide, 300 high. The SVG stretches to the
page width (preserveAspectRatio="none"), and lines keep their thickness through
`vector-effect: non-scaling-stroke` in the CSS.
"""

from __future__ import annotations

from collections.abc import Sequence

WIDTH = 1000.0
HEIGHT = 300.0


def _scale(values: Sequence[float]) -> tuple[float, float]:
    """Lowest and highest value with a little air, so lines do not touch the edge."""
    low, high = min(values), max(values)
    pad = (high - low) * 0.08 or 1.0
    return low - pad, high + pad


def _points(xs: Sequence[float], ys: Sequence[float], low: float, high: float) -> str:
    x0, x1 = xs[0], xs[-1]
    span = (x1 - x0) or 1.0
    return " ".join(
        f"{(x - x0) / span * WIDTH:.1f},{HEIGHT - (y - low) / (high - low) * HEIGHT:.1f}"
        for x, y in zip(xs, ys, strict=True)
    )


def value_chart(series: dict) -> dict:
    """Portfolio against benchmark. `series` has the API shape: dates, portfolio, benchmark."""
    xs = list(range(len(series["dates"])))
    everything = [*series["portfolio"], *series["benchmark"]]
    low, high = _scale(everything)
    return {
        "portfolio": _points(xs, series["portfolio"], low, high),
        "benchmark": _points(xs, series["benchmark"], low, high),
        "min": min(everything),
        "max": max(everything),
        "start": series["dates"][0],
        "end": series["dates"][-1],
    }


def fan_chart(outlook: dict) -> dict:
    """Range of outcomes. `outlook` has the API shape: months, p5, p25, p50, p75, p95."""
    xs = outlook["months"]
    low, high = _scale([*outlook["p5"], *outlook["p95"]])

    def band(lower: Sequence[float], upper: Sequence[float]) -> str:
        there = _points(xs, upper, low, high)
        back = " ".join(reversed(_points(xs, lower, low, high).split(" ")))
        return f"{there} {back}"

    return {
        "wide": band(outlook["p5"], outlook["p95"]),
        "mid": band(outlook["p25"], outlook["p75"]),
        "median": _points(xs, outlook["p50"], low, high),
        "min": min(outlook["p5"]),
        "max": max(outlook["p95"]),
    }


def allocation_bar(allocation: Sequence[dict], gap: float = 2.0) -> list[dict]:
    """One rectangle per position for the thin allocation bar (1000 wide)."""
    bars, x = [], 0.0
    for position in allocation:
        width = position["weight"] * WIDTH
        bars.append(
            {
                "x": round(x, 1),
                "width": round(max(width - gap, 0.5), 1),
                "role": position["role"],
            }
        )
        x += width
    return bars
