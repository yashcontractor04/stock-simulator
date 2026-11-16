"""How numbers and dates are written on the pages.

Frontend helper, built by Fable. Registered as Jinja filters in templating.py:
    {{ 28140.55 | money }}      $28,141
    {{ 28140.55 | money2 }}     $28,140.55
    {{ 0.1090 | pct }}          +10.9%
    {{ 0.30 | share }}          30%
    {{ "2026-11-13" | day }}    Nov 13, 2026
English only for now.
"""

from __future__ import annotations

import datetime as dt

_MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
_DASH = "–"


def money(value: float | None) -> str:
    if value is None:
        return _DASH
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def money2(value: float | None) -> str:
    if value is None:
        return _DASH
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def pct(value: float | None, digits: int = 1) -> str:
    """A change as a signed percentage: 0.109 -> +10.9%."""
    if value is None:
        return _DASH
    text = f"{value * 100:+.{digits}f}%"
    return (
        text.replace("+0.0%", "0.0%").replace("-0.0%", "0.0%") if digits == 1 else text
    )


def share(value: float | None, digits: int = 0) -> str:
    """A part of a whole, without a sign: 0.3 -> 30%."""
    return _DASH if value is None else f"{value * 100:.{digits}f}%"


def number(value: float | None, digits: int = 2) -> str:
    return _DASH if value is None else f"{value:,.{digits}f}"


def tone(value: float | None) -> str:
    """CSS class for a gain or a loss. Green and red mean nothing else on the site."""
    if value is None or value == 0:
        return "mute"
    return "pos" if value > 0 else "neg"


def day(value: str | dt.date | None) -> str:
    if value is None:
        return _DASH
    d = dt.date.fromisoformat(value[:10]) if isinstance(value, str) else value
    return f"{_MONTHS[d.month - 1]} {d.day}, {d.year}"


def moment(value: str | dt.datetime | None) -> str:
    """A date and time in UTC: Nov 14, 2026 03:41 UTC."""
    if value is None:
        return _DASH
    t = (
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if isinstance(value, str)
        else value
    )
    return f"{day(t.date())} {t:%H:%M} UTC"


FILTERS = {
    "money": money,
    "money2": money2,
    "pct": pct,
    "share": share,
    "number": number,
    "tone": tone,
    "day": day,
    "moment": moment,
}
