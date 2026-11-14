"""Acceptance tests for the M8 CLI surface (SPEC M2 / PLAN milestone M8)."""

from __future__ import annotations

import io
import json
import shutil
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from govern import config, run, session, tasks
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
CONFIG = config.load(ROOT / "config" / "config.json")
RUNS = ROOT / "runs"


def _run_id() -> str:
    return f"R-T{uuid.uuid4().hex[:8]}"


def _clean(run_id: str) -> None:
    shutil.rmtree(RUNS / run_id, ignore_errors=True)


def _call(*argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        code = run.main(list(argv))
    return code, buffer.getvalue()


def _logs(run_id: str) -> list[Path]:
    return sorted((RUNS / run_id / "logs").rglob("*.jsonl"))


class SelftestTests(unittest.TestCase):
    def test_selftest_reports_the_corpus_and_the_cards(self):
        code, out = _call("--selftest")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), f"ok: {len(tasks.load_index(ROOT / 'corpus'))} tasks, 6 cards")

    def test_dry_run_writes_nothing(self):
        before = len(list((ROOT / "runs").rglob("*.jsonl"))) if (ROOT / "runs").exists() else 0
        code, out = _call("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("no logs written", out)
        after = len(list((ROOT / "runs").rglob("*.jsonl"))) if (ROOT / "runs").exists() else 0
        self.assertEqual(before, after)


class SimulateCliTests(unittest.TestCase):
    def test_simulate_prints_the_balance_and_writes_a_report(self):
        code, out = _call("--simulate", "40")
        self.assertEqual(code, 0)
        self.assertIn("chi2 p=", out)
        report_path = RUNS / "_sim" / "sim.json"
        self.assertTrue(report_path.is_file())
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["n"], 40)
        self.assertGreater(report["p"], CONFIG.alpha_sim)


class SessionCliTests(unittest.TestCase):
    def test_a_headless_session_writes_a_complete_log(self):
        run_id = _run_id()
        try:
            code, out = _call(
                "--session", "S-CLI1", "--participant", "P01", "--condition", "C1",
                "--task", "T-L01a", "--run-id", run_id,
            )
            self.assertEqual(code, 0, out)
            logs = _logs(run_id)
            self.assertEqual(len(logs), 1)
            events = [json.loads(line) for line in logs[0].read_text(encoding="utf-8").splitlines()]
            kinds = [e["event_type"] for e in events]
            self.assertEqual(kinds[0], "session_start")
            self.assertEqual(kinds[-1], "session_end")
            self.assertIn("gate_decision", kinds)
            self.assertIn("task_end", kinds)
        finally:
            _clean(run_id)

    def test_without_consent_the_session_is_refused(self):
        run_id = _run_id()
        try:
            code, out = _call(
                "--session", "S-CLI2", "--participant", "P01", "--condition", "C1",
                "--task", "T-L01a", "--run-id", run_id, "--no-consent",
            )
            self.assertNotEqual(code, 0)
            self.assertIn("consent", out.lower())
            self.assertEqual(_logs(run_id), [])
        finally:
            _clean(run_id)

    def test_an_unknown_task_is_a_usage_error(self):
        code, out = _call(
            "--session", "S-CLI3", "--participant", "P01", "--condition", "C1",
            "--task", "T-NOPE", "--run-id", _run_id(),
        )
        self.assertEqual(code, run.EXIT_USAGE)
        self.assertIn("T-NOPE", out)


class WebCliTests(unittest.TestCase):
    """``--port`` serves the UI instead of rehearsing; the server is stubbed here.

    The HTTP transport itself is covered in ``tests/test_web.py``; what matters
    at this layer is that the CLI builds and starts the same ``Session`` the
    other paths use, and closes the log honestly when the server stops.
    """

    def test_port_serves_the_session_it_started(self):
        run_id = _run_id()
        try:
            with mock.patch.object(run.web, "serve", return_value=0) as serve:
                code, out = _call(
                    "--session", "S-UI1", "--participant", "P01", "--condition", "C1",
                    "--task", "T-L01a", "--port", "8123", "--run-id", run_id,
                )
            self.assertEqual(code, 0, out)
            self.assertEqual(serve.call_args.args[1], 8123)
            served = serve.call_args.args[0]
            self.assertEqual(served.condition, "C1")
            kinds = [json.loads(line)["event_type"] for line in _logs(run_id)[0].read_text(encoding="utf-8").splitlines()]
            self.assertEqual(kinds[0], "session_start")
            self.assertEqual(kinds[-1], "session_end")
            end = json.loads(_logs(run_id)[0].read_text(encoding="utf-8").splitlines()[-1])
            self.assertFalse(end["completed_all"])
            self.assertTrue(end["withdrawn"], "leaving before 'Finish' is a withdrawal, not a completion")
        finally:
            _clean(run_id)


class BatchCliTests(unittest.TestCase):
    def _schedule(self, tmp: Path) -> Path:
        path = tmp / "schedule.json"
        path.write_text(
            json.dumps(
                {
                    "schedule_id": "SCH-TEST",
                    "seed": 42,
                    "pairs": ["PAIR-01"],
                    "participants": ["P01"],
                    "orders": ["AB"],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_batch_runs_every_slot_of_the_schedule(self):
        run_id = _run_id()
        try:
            with scratch_dir("batch") as tmp:
                code, out = _call(
                    "--batch", "--schedule", str(self._schedule(tmp)),
                    "--participant", "P01", "--run-id", run_id,
                )
            self.assertEqual(code, 0, out)
            self.assertEqual(len(_logs(run_id)), 2)
        finally:
            _clean(run_id)

    def test_resume_finishes_a_checkpointed_session(self):
        run_id = _run_id()
        try:
            with scratch_dir("resume-cli") as tmp:
                sess = session.Session(
                    RUNS / run_id,
                    tasks.by_id(tasks.load_index(ROOT / "corpus"), "T-L01a"),
                    "C1",
                    "P01",
                    run.log_for(RUNS / run_id, "S-CLI4", "P01", "C1"),
                )
                sess.start(run.consent_for(CONFIG, run_id))
                sess.submit_prompt("Refactor.")
                state = tmp / "S-CLI4.json"
                sess.checkpoint(state)

                code, out = _call("--resume", str(state))
                self.assertEqual(code, 0, out)
                events = [
                    json.loads(line)
                    for line in sess.logger.path.read_text(encoding="utf-8").splitlines()
                ]
                self.assertEqual(events[-1]["event_type"], "session_end")
                self.assertEqual([e["seq"] for e in events], list(range(1, len(events) + 1)))
        finally:
            _clean(run_id)


if __name__ == "__main__":
    unittest.main()
