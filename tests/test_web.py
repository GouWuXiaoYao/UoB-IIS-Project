"""Acceptance tests for the web UI (SPEC M9 / PLAN milestone M9).

The UI is a thin shell over ``Session``: it must never be able to bypass the
gate, and every click must land in the same JSONL log a CLI run would write.
These tests drive the real HTTP server over a loopback socket -- no mocking of
the transport -- because the interesting failures (a route that forgets to check
``gate.open()``, a body that 200s on a refusal) only show up end to end.
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from govern import config, log, session, tasks, web
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
CONFIG = config.load(ROOT / "config" / "config.json")
TASKS = tasks.load_index(ROOT / "corpus")

CONSENT = {
    "consent_version": "SIM-AUTHOR",
    "consent_given": True,
    "prior_years": 0.0,
    "llm_freq": "never",
    "lang_familiarity": 5,
    "schedule_id": "SCH-01",
    "device": "author-workstation",
}


def _logger(run_dir: Path, condition: str = "C1") -> log.Logger:
    return log.Logger(
        run_dir,
        {
            "session_id": f"S-P01-{condition}",
            "participant_id": "P01",
            "condition": condition,
            "app_version": CONFIG.app_version,
            "model_id": CONFIG.model_id,
            "model_temperature": CONFIG.temperature,
            "seed": CONFIG.seed,
        },
    )


def _events(logger: log.Logger) -> list[dict]:
    return [json.loads(line) for line in logger.path.read_text(encoding="utf-8").splitlines() if line]


class _Served:
    """A real HTTP server on an ephemeral loopback port, torn down per test."""

    def __init__(self, app: web.App) -> None:
        self.server = web.make_server(app, port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def raw(self, method: str, path: str, body: dict | None = None) -> tuple[int, str]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8")

    def call(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        status, text = self.raw(method, path, body)
        return status, json.loads(text)

    def refused(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        """Same as ``call`` but for the 4xx paths urllib raises on."""
        try:
            status, text = self.raw(method, path, body)
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        raise AssertionError(f"expected a refusal, got HTTP {status} for {path}")


class _Base(unittest.TestCase):
    condition = "C1"

    def setUp(self) -> None:
        self._ctx = scratch_dir()
        self.run_dir = Path(self._ctx.__enter__())
        self.logger = _logger(self.run_dir, self.condition)
        self.session = session.Session(
            self.run_dir,
            tasks.by_id(TASKS, "T-L01a"),
            self.condition,
            "P01",
            self.logger,
        )
        self.session.start(CONSENT)
        self.app = web.App(self.session)
        self.served = _Served(self.app)

    def tearDown(self) -> None:
        self.served.close()
        self._ctx.__exit__(None, None, None)

    # -- helpers ---------------------------------------------------------
    def prompt(self) -> dict:
        status, body = self.served.call("POST", "/api/prompt", {"text": "make the totals integral"})
        self.assertEqual(status, 200)
        return body

    def confirm_all(self) -> dict:
        for item in self.prompt()["items"]:
            self.served.call("POST", "/api/toggle", {"item_id": item["item_id"]})
        status, decision = self.served.call("POST", "/api/confirm", {})
        self.assertEqual(status, 200)
        return decision


class IndexTests(_Base):
    def test_the_page_is_served_from_static(self) -> None:
        status, html = self.served.raw("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Assessment card", html)
        self.assertIn('data-app="govern-ui"', html)

    def test_the_page_declares_the_backend_it_talks_to(self) -> None:
        _, html = self.served.raw("GET", "/")
        self.assertIn("/api/prompt", html)
        self.assertIn("/api/toggle", html)
        self.assertIn("/api/confirm", html)
        self.assertIn("/api/generate", html)


class CardRouteTests(_Base):
    def test_prompt_returns_every_card_item_unchecked(self) -> None:
        body = self.prompt()
        self.assertEqual(len(body["items"]), len(self.session.card.items))
        self.assertTrue(all(item["checked"] is False for item in body["items"]))
        self.assertEqual(body["n_required"], self.session.card.n_required)
        self.assertTrue(body["impact_set_hash"].startswith("sha256:"))

    def test_prompt_logs_the_prompt_and_the_card(self) -> None:
        self.prompt()
        kinds = [event["event_type"] for event in _events(self.logger)]
        self.assertIn("prompt_submit", kinds)
        self.assertIn("card_shown", kinds)

    def test_toggle_returns_the_running_count_and_the_missing_items(self) -> None:
        items = self.prompt()["items"]
        status, body = self.served.call("POST", "/api/toggle", {"item_id": items[0]["item_id"]})
        self.assertEqual(status, 200)
        self.assertTrue(body["checked"])
        self.assertEqual(body["n_confirmed"], 1)
        self.assertIn(items[1]["item_id"], body["missing"])

    def test_an_unknown_item_is_a_400(self) -> None:
        self.prompt()
        status, body = self.served.refused("POST", "/api/toggle", {"item_id": "CI-999"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "unknown_item")


class GateRouteTests(_Base):
    def test_generating_before_confirming_is_refused(self) -> None:
        self.prompt()
        status, body = self.served.refused("POST", "/api/generate", {})
        self.assertEqual(status, 409)
        self.assertEqual(body["error"], "gate_closed")
        self.assertTrue(body["missing"])

    def test_generating_after_a_partial_confirmation_is_refused(self) -> None:
        items = self.prompt()["items"]
        self.served.call("POST", "/api/toggle", {"item_id": items[0]["item_id"]})
        status, body = self.served.refused("POST", "/api/generate", {})
        self.assertEqual(status, 409)
        self.assertEqual(len(body["missing"]), len(items) - 1)

    def test_confirming_every_item_opens_the_gate_and_generation_succeeds(self) -> None:
        decision = self.confirm_all()
        self.assertFalse(decision["blocked"])
        self.assertTrue(decision["confirmed"])
        status, body = self.served.call("POST", "/api/generate", {})
        self.assertEqual(status, 200)
        self.assertIn("patch_diff", body)
        self.assertTrue(body["rationale_text"])
        self.assertGreaterEqual(len(body["touched_symbols"]), 1)

    def test_a_blocked_decision_is_logged_as_blocked(self) -> None:
        self.prompt()
        self.served.refused("POST", "/api/generate", {})
        blocked = [e for e in _events(self.logger) if e["event_type"] == "gate_decision"]
        self.assertTrue(blocked)
        self.assertTrue(blocked[-1]["blocked"])


class BaselineConditionTests(_Base):
    condition = "C0"

    def test_the_baseline_condition_shows_no_card(self) -> None:
        body = self.prompt()
        self.assertEqual(body["items"], [])
        self.assertEqual(body["n_required"], 0)
        self.assertEqual(body["condition"], "C0")

    def test_the_baseline_condition_generates_without_confirming(self) -> None:
        self.prompt()
        status, body = self.served.call("POST", "/api/generate", {})
        self.assertEqual(status, 200)
        self.assertIn("patch_diff", body)


class ActRouteTests(_Base):
    def test_accepting_applies_the_patch_and_reports_the_hidden_suite(self) -> None:
        self.confirm_all()
        _, suggestion = self.served.call("POST", "/api/generate", {})
        status, body = self.served.call(
            "POST",
            "/api/act",
            {"suggestion_id": suggestion["suggestion_id"], "action": "accept", "dwell_ms": 1200},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["action"], "accept")
        self.assertTrue(body["applied"])

    def test_an_unknown_action_is_a_400(self) -> None:
        self.confirm_all()
        _, suggestion = self.served.call("POST", "/api/generate", {})
        status, body = self.served.refused(
            "POST",
            "/api/act",
            {"suggestion_id": suggestion["suggestion_id"], "action": "vibe", "dwell_ms": 1},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "bad_action")

    def test_rejecting_leaves_the_worktree_alone(self) -> None:
        self.confirm_all()
        _, suggestion = self.served.call("POST", "/api/generate", {})
        before = sorted(p.name for p in (self.session.work).rglob("*.py"))
        self.served.call(
            "POST",
            "/api/act",
            {"suggestion_id": suggestion["suggestion_id"], "action": "reject", "dwell_ms": 900},
        )
        self.assertEqual(before, sorted(p.name for p in (self.session.work).rglob("*.py")))


class EndRouteTests(_Base):
    def test_ending_reports_the_outcome_and_closes_the_log(self) -> None:
        self.confirm_all()
        _, suggestion = self.served.call("POST", "/api/generate", {})
        self.served.call(
            "POST",
            "/api/act",
            {"suggestion_id": suggestion["suggestion_id"], "action": "accept", "dwell_ms": 800},
        )
        status, body = self.served.call("POST", "/api/end", {})
        self.assertEqual(status, 200)
        self.assertIn("tests_pass", body)
        kinds = [event["event_type"] for event in _events(self.logger)]
        self.assertEqual(kinds[0], "session_start")
        self.assertEqual(kinds[-1], "task_end")

    def test_a_second_end_is_refused(self) -> None:
        self.served.call("POST", "/api/end", {})
        status, body = self.served.refused("POST", "/api/end", {})
        self.assertEqual(status, 409)
        self.assertEqual(body["error"], "already_ended")


class StateRouteTests(_Base):
    def test_state_is_the_log_backed_state(self) -> None:
        self.prompt()
        status, body = self.served.call("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(body["condition"], "C1")
        self.assertEqual(body["phase"], "card")
        self.assertEqual(body["card_id"], self.session.card.card_id)
        self.assertFalse(body["ended"])

    def test_an_unknown_route_is_404(self) -> None:
        status, body = self.served.refused("GET", "/api/nope")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "not_found")


class HygieneTests(unittest.TestCase):
    def test_the_server_binds_loopback_only(self) -> None:
        with scratch_dir() as run_dir:
            logger = _logger(Path(run_dir))
            sess = session.Session(
                Path(run_dir), tasks.by_id(TASKS, "T-L01a"), "C1", "P01", logger
            )
            server = web.make_server(web.App(sess), port=0)
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
            finally:
                server.server_close()

    def test_no_endpoint_or_key_literal_in_the_web_layer(self) -> None:
        from tools import scan_secrets

        offenders = []
        paths = sorted((ROOT / "static").rglob("*")) + [ROOT / "govern" / "web.py"]
        for path in paths:
            if not path.is_file():
                continue
            for _name, lineno, line in scan_secrets.scan_text(path.read_text(encoding="utf-8")):
                offenders.append(f"{path.name}:{lineno}: {line}")
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_the_page_never_ships_a_pre_ticked_checkbox(self) -> None:
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('checked="checked"', html)
        self.assertNotIn("checked>", html)


if __name__ == "__main__":
    unittest.main()
