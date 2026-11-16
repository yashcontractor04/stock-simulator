"""Builds the Jinja2 environment for the pages.

Frontend helper, built by Fable. The backend uses it like this (sketch):

    from fastapi.templating import Jinja2Templates
    from sim.web.templating import create_environment

    templates = Jinja2Templates(env=create_environment())

Autoescaping is on for every template, so a value can never become HTML by
accident. Do not use the `|safe` filter in templates.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import charts
from .filters import FILTERS

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

RISK_NAMES = {"low": "Low risk", "medium": "Medium risk", "high": "High risk"}


def create_environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
        undefined=StrictUndefined,  # a missing value is an error, not an empty string
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(FILTERS)
    env.globals.update(
        value_chart=charts.value_chart,
        fan_chart=charts.fan_chart,
        allocation_bar=charts.allocation_bar,
        risk_names=RISK_NAMES,
    )
    return env
