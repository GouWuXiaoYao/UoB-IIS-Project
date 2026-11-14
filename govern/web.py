"""Web UI for one author self-test session (SPEC M9 / PLAN milestone M9).

The browser is a *view* over ``session.Session``, nothing more. Every route below
delegates to a method that already writes its own telemetry, so a click in the
page produces exactly the same JSONL a CLI run would -- and the gate cannot be
bypassed by crafting an HTTP request, because ``/api/generate`` is refused when
``Gate.open()`` is false regardless of what the page sends.

Served on loopback only: this is a local prototype, not a hosted service, and
binding wider would expose a run log containing card items to the network.
"""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import gate as gate_mod, session as session_mod

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
INDEX = STATIC / "index.html"
DEFAULT_HOST = "127.0.0.1"
ACTIONS = ("accept", "edit", "reject")


class ApiError(Exception):
    """An HTTP-level refusal the page can render without guessing."""

    def __init__(self, status: HTTPStatus, error: str, **extra: Any) -> None:
        super().__init__(error)
        self.status = int(status)
        self.payload: dict[str, Any] = {"error": error, **extra}


def _missing(sess: session_mod.Session) -> list[str]:
    """Required items the participant has not confirmed yet, in card order."""
    confirmed = set(sess.gate.confirmed_ids())
    return [item.item_id for item in sess.card.items if item.required and item.item_id not in confirmed]


class App:
    """Route table for one ``Session``. Transport-agnostic on purpose: testable."""

    def __init__(self, sess: session_mod.Session) -> None:
        self.session = sess

    # -- views -----------------------------------------------------------
    def index(self) -> str:
        return INDEX.read_text(encoding="utf-8")

    def card_view(self) -> dict[str, Any]:
        confirmed = set(self.session.gate.confirmed_ids())
        pending = self.session.last_suggestion()
        return {
            "condition": self.session.condition,
            "card_id": self.session.card.card_id,
            "card_version": self.session.card.version,
            "impact_set_hash": self.session.impact_hash,
            "n_items": self.session.card.n_items,
            "n_required": self.session.card.n_required,
            "gate_open": bool(self.session.gate.open()),
            "missing": _missing(self.session),
            "last_action": self.session.state()["last_action"],
            "suggestion": (
                None
                if pending is None
                else {
                    "suggestion_id": pending.suggestion_id,
                    "patch_diff": pending.patch_diff,
                    "rationale_text": pending.rationale_text,
                }
            ),
            "items": [
                {
                    "item_id": item.item_id,
                    "statement": item.statement,
                    "category": item.category,
                    "affected_symbol": item.affected_symbol,
                    "evidence_ref": item.evidence_ref,
                    "required": bool(item.required),
                    "checked": item.item_id in confirmed,
                }
                for item in self.session.card.items
            ],
        }

    def state(self) -> dict[str, Any]:
        state = dict(self.session.state())
        state["condition"] = self.session.condition
        state["participant"] = self.session.participant
        state["task_id"] = self.session.task.task_id
        return state

    def card(self) -> dict[str, Any]:
        """The card as it currently stands.

        Exists so a page can be re-rendered from server state alone -- used by
        the storyboard capture, where nobody is clicking.
        """
        return self.card_view()

    # -- routes ----------------------------------------------------------
    def prompt(self, body: dict[str, Any]) -> dict[str, Any]:
        text = str(body.get("text", "")).strip()
        if not text:
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad_request", detail="text is required")
        self.session.submit_prompt(text)
        return self.card_view()

    def toggle(self, body: dict[str, Any]) -> dict[str, Any]:
        item_id = str(body.get("item_id", "")).strip()
        if not item_id:
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad_request", detail="item_id is required")
        try:
            checked, decision = self.session.toggle(item_id)
        except KeyError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "unknown_item", item_id=item_id) from None
        return {
            "item_id": item_id,
            "checked": bool(checked),
            "n_confirmed": decision.n_confirmed,
            "n_required": decision.n_required,
            "blocked": bool(decision.blocked),
            "missing": _missing(self.session),
            "gate_open": bool(self.session.gate.open()),
        }

    def confirm(self, body: dict[str, Any]) -> dict[str, Any]:
        decision = self.session.confirm()
        return {
            "confirmed": bool(decision.confirmed),
            "blocked": bool(decision.blocked),
            "n_confirmed": decision.n_confirmed,
            "n_required": decision.n_required,
            "missing": _missing(self.session),
            "gate_open": bool(self.session.gate.open()),
        }

    def generate(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            suggestion = self.session.generate()
        except session_mod.GateClosed as exc:  # the one refusal that must never be silent
            raise ApiError(
                HTTPStatus.CONFLICT, "gate_closed", detail=str(exc), missing=_missing(self.session)
            ) from exc
        return {
            "suggestion_id": suggestion.suggestion_id,
            "patch_diff": suggestion.patch_diff,
            "rationale_text": suggestion.rationale_text,
            "touched_symbols": list(suggestion.touched_symbols),
            "layers": list(suggestion.layers),
        }

    def act(self, body: dict[str, Any]) -> dict[str, Any]:
        action = str(body.get("action", "")).strip()
        if action not in ACTIONS:
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad_action", detail=f"action must be one of {ACTIONS}")
        suggestion_id = str(body.get("suggestion_id", "")).strip()
        if not suggestion_id:
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad_request", detail="suggestion_id is required")
        dwell_ms = int(body.get("dwell_ms", 0) or 0)
        edit_lines = body.get("edit_lines")
        self.session.act(
            suggestion_id,
            action,
            dwell_ms,
            edit_lines=None if edit_lines is None else int(edit_lines),
        )
        return {
            "action": action,
            "suggestion_id": suggestion_id,
            "applied": action in ("accept", "edit"),
            "n_events": self.session.state()["n_events"],
        }

    def end(self, body: dict[str, Any]) -> dict[str, Any]:
        if self.session.state()["ended"]:
            raise ApiError(HTTPStatus.CONFLICT, "already_ended")
        outcome = self.session.end(submitted=bool(body.get("submitted", True)))
        return {**outcome.as_dict(), "ended": True}

    # -- dispatch --------------------------------------------------------
    _GET = {"/api/state": "state", "/api/card": "card"}
    _POST = {
        "/api/prompt": "prompt",
        "/api/toggle": "toggle",
        "/api/confirm": "confirm",
        "/api/generate": "generate",
        "/api/act": "act",
        "/api/end": "end",
    }

    def handle(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        """Return ``(status, payload)`` for one request; never raises."""
        try:
            if method == "GET":
                if path in ("/", "/index.html"):
                    return int(HTTPStatus.OK), {"html": self.index()}
                name = self._GET.get(path)
                if name is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, "not_found", path=path)
                return int(HTTPStatus.OK), getattr(self, name)()
            if method == "POST":
                name = self._POST.get(path)
                if name is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, "not_found", path=path)
                return int(HTTPStatus.OK), getattr(self, name)(body or {})
            raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "bad_method", method=method)
        except ApiError as exc:
            return exc.status, exc.payload


class Handler(BaseHTTPRequestHandler):
    """One request. JSON in, JSON out; the page itself is the only HTML."""

    server_version = "govern-ui/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003 - stdlib signature
        del fmt, args  # the run log is the record; the console is not

    # -- plumbing --------------------------------------------------------
    def _send(self, status: int, payload: dict[str, Any] | str, content_type: str) -> None:
        raw = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad_json") from None
        if not isinstance(payload, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad_json", detail="expected an object")
        return payload

    def _dispatch(self, method: str) -> None:
        app: App = self.server.app  # type: ignore[attr-defined]
        path = self.path.split("?", 1)[0]
        try:
            body = self._body() if method == "POST" else None
        except ApiError as exc:
            self._send(exc.status, exc.payload, "application/json")
            return
        status, payload = app.handle(method, path, body)
        if status == int(HTTPStatus.OK) and "html" in payload and len(payload) == 1:
            self._send(status, payload["html"], "text/html; charset=utf-8")
            return
        self._send(status, payload, "application/json")

    def do_GET(self) -> None:  # noqa: N802 - stdlib signature
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802 - stdlib signature
        self._dispatch("POST")


class GovernServer(ThreadingHTTPServer):
    """``ThreadingHTTPServer`` that carries the app it serves."""

    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: App) -> None:
        super().__init__(address, Handler)
        self.app = app


def make_server(app: App, port: int, host: str = DEFAULT_HOST) -> GovernServer:
    """Bind a loopback server; ``port=0`` asks the OS for a free one."""
    return GovernServer((host, int(port)), app)


def serve(sess: session_mod.Session, port: int, host: str = DEFAULT_HOST) -> int:
    """Serve until Ctrl-C. Prints the real URL first (port 0 means 'pick one')."""
    server = make_server(App(sess), port, host)
    bound_host, bound_port = server.server_address[0], server.server_address[1]
    print(f"serving http://{bound_host}:{bound_port}/ for {sess.task.task_id} ({sess.condition})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    finally:
        server.server_close()
    return 0


def _selftest() -> int:
    """Offline check: the page exists and declares every route the app answers."""
    html = INDEX.read_text(encoding="utf-8")
    missing = [route for route in App._POST if route not in html]
    if missing:
        print(f"fail: static/index.html does not call {', '.join(missing)}")
        return 1
    if "checkbox" not in html:
        print("fail: static/index.html has no checkbox control")
        return 1
    print(f"ok: {len(App._POST)} routes wired, card rendered from session state")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m govern.web")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
