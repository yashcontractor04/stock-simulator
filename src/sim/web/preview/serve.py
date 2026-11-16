"""A tiny stand-in server to look at the pages before the real backend exists.

Frontend helper, built by Fable. NOT part of the backend: it uses only the Python
standard library plus Jinja2 and PyYAML, knows no database, and fakes everything
with sample data from the API contract (see mock.py).

    pip install jinja2 pyyaml
    python -m sim.web.preview.serve          (from the src/ folder)
    open http://localhost:8001

It sends the same security headers the real app must send, so a template that
breaks the Content-Security-Policy shows up here first (browser console).

Pages to look at:
    /                        dashboard            /?empty=1        before the first snapshot
    /simulate                the form             /simulate?errors=1   /simulate?disabled=1
    /simulations/demo        fakes queued -> running -> finished over a few seconds
    /simulations/failed      a failed simulation
    /about
    /admin/login             any password works here
    /admin  /admin/jobs  /admin/settings
    /preview/404  /preview/429  /preview/500  /preview/503
"""

from __future__ import annotations

import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from ..templating import STATIC_DIR, create_environment
from . import mock

ENV = create_environment()
DATA = mock.load()
POLLS = {"count": 0}  # how often the demo simulation was asked for its status

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
    "font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-Frame-Options": "DENY",
}
ERRORS = {
    "404": ("Not found", "There is nothing at this address.", None),
    "429": (
        "Too many requests",
        "You have started several simulations in a short time.",
        240,
    ),
    "500": (
        "Something went wrong",
        "That is a bug on my side. It has been logged.",
        None,
    ),
    "503": (
        "Busy right now",
        "Many simulations are waiting. Please try again in a moment.",
        60,
    ),
}


def demo_simulation() -> dict:
    """Pretends the job moves along: the 1st look is queued, then running, then done."""
    POLLS["count"] += 1
    if POLLS["count"] <= 1:
        return DATA["simulation_queued"]
    if POLLS["count"] <= 3:
        return {**DATA["simulation_running"], "progress": 0.3 * (POLLS["count"] - 1)}
    return DATA["simulation_succeeded"]


def render(path: str, query: dict) -> tuple[int, str] | None:
    flag = lambda name: name in query
    page = lambda template, **context: ENV.get_template(template).render(
        sample=True, **context
    )
    admin = {"admin": True, "csrf_token": "preview-csrf-token-not-a-real-one"}

    if path == "/":
        selected = query.get("risk", ["medium"])[0]
        selected = selected if selected in ("low", "medium", "high") else "medium"
        return 200, page(
            "dashboard.html",
            nav="dashboard",
            snapshot=None if flag("empty") else DATA["snapshot"],
            selected=selected,
        )
    if path == "/simulate":
        values = {
            "capital": 10000,
            "risk_level": "medium",
            "time_span_years": 10,
            "industries": ["healthcare", "technology"],
            "themes": [],
        }
        errors = {}
        if flag("errors"):
            values = {**values, "capital": 5, "time_span_years": 40}
            errors = {
                "capital": "Must be between $100 and $10,000,000.",
                "time_span_years": "Must be between 1 and 20.",
            }
        return 200, page(
            "simulate.html",
            nav="simulate",
            options=DATA["options"],
            values=values,
            errors=errors,
            enabled=not flag("disabled"),
            idempotency_key="preview-0001",
        )
    if path == "/simulations/demo":
        POLLS["count"] = 0
        return 200, page(
            "simulation.html", nav="simulate", simulation=demo_simulation()
        )
    if path.startswith("/simulations/") and path.endswith(
        "/status"
    ):  # the id in the sample data differs from "demo"
        return 200, page("_simulation_status.html", simulation=demo_simulation())
    if path == "/simulations/failed":
        return 200, page(
            "simulation.html", nav="simulate", simulation=DATA["simulation_failed"]
        )
    if path == "/about":
        return 200, page("about.html", nav="about")
    if path == "/admin/login":
        return 200, page(
            "admin/login.html",
            nav="",
            error="Wrong password." if flag("error") else None,
            locked=False,
        )
    if path == "/admin":
        return 200, page(
            "admin/status.html",
            nav="admin-status",
            status=DATA["admin_status"],
            **admin,
        )
    if path == "/admin/jobs":
        return 200, page(
            "admin/jobs.html",
            nav="admin-jobs",
            jobs=DATA["jobs"],
            kinds=DATA["job_kinds"],
            **admin,
        )
    if path == "/admin/settings":
        return 200, page(
            "admin/settings.html",
            nav="admin-settings",
            settings=DATA["settings"],
            errors={},
            saved=flag("saved"),
            **admin,
        )
    if path.startswith("/preview/") and path.removeprefix("/preview/") in ERRORS:
        code = path.removeprefix("/preview/")
        title, detail, retry = ERRORS[code]
        return int(code), page(
            "error.html",
            nav="",
            status_code=code,
            title=title,
            detail=detail,
            retry_after=retry,
        )
    return None


REDIRECTS = {
    "/simulate": "/simulations/demo",
    "/admin/login": "/admin",
    "/admin/logout": "/",
    "/admin/jobs": "/admin/jobs",
    "/admin/settings": "/admin/settings?saved=1",
}


class Handler(BaseHTTPRequestHandler):
    def _send(
        self, status: int, body: bytes, content_type: str, extra: dict | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in {**SECURITY_HEADERS, **(extra or {})}.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path.startswith("/static/"):
            file = (STATIC_DIR / url.path.removeprefix("/static/")).resolve()
            if STATIC_DIR in file.parents and file.is_file():
                kind = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                return self._send(200, file.read_bytes(), kind)
        result = render(url.path, parse_qs(url.query, keep_blank_values=True))
        if result is None:
            result = render("/preview/404", {})
        status, html = result
        self._send(
            status,
            html.encode(),
            "text/html; charset=utf-8",
            {"Cache-Control": "no-store"},
        )

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        target = REDIRECTS.get(urlparse(self.path).path, "/")
        self.send_response(
            303
        )  # "see other": after a form post, send the browser to a normal page
        self.send_header("Location", target)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args) -> None:  # keep the terminal quiet
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f"Preview with sample data on http://localhost:{port}  (Ctrl+C stops it)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
