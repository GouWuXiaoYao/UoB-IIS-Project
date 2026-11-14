"""The six completion definitions, one test each (PLAN milestone M11).

PLAN §1 lists six conditions that define "done". Five of them can be run as a
subprocess from here; the first one is the suite you are reading, so it is
checked by re-running discovery over a single file (running the whole suite from
inside the suite would recurse).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from govern import log
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent


def _run(*argv: str, timeout: int = 600) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env.pop("A2_API_KEY", None)
    env.pop("A2_API_BASE", None)
    completed = subprocess.run(
        [sys.executable, *argv],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
    )
    return completed.returncode, completed.stdout + completed.stderr


class CompletionDefinitionTests(unittest.TestCase):
    def test_1_the_test_command_runs_the_suite(self):
        # The full suite is this very process; discovery is proven on one module.
        code, out = _run("-m", "unittest", "discover", "-s", "tests", "-q", "-p", "test_smoke.py")
        self.assertEqual(code, 0, out)
        self.assertIn("OK", out)

    def test_2_one_command_self_test(self):
        code, out = _run("-m", "govern.run", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("ok: 6 tasks, 6 cards", out)
        self.assertIn("no logs written", out)

    def test_3_one_command_reproduces_a_batch_without_network_or_key(self):
        run_id = "R-E2E"
        code, out = _run(
            "-m", "govern.run", "--batch", "--participant", "P01",
            "--schedule", "config/schedule.json", "--run-id", run_id,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("ok: batch P01 ran", out)
        logs = sorted((ROOT / "runs" / run_id / "logs").rglob("*.jsonl"))
        self.assertEqual(len(logs), 6, [str(p) for p in logs])
        for path in logs:
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(events[0]["event_type"], "session_start")
            self.assertEqual(events[-1]["event_type"], "session_end")
            for event in events:
                self.assertEqual(log.validate(event), [])

    def test_4_every_experiment_parameter_comes_from_config(self):
        # A source scan for the five values that would be most tempting to inline.
        offenders: list[str] = []
        for path in sorted((ROOT / "govern").glob("*.py")):
            if path.name == "config.py":
                continue
            text = path.read_text(encoding="utf-8")
            for needle in ("3000", "1800", "0.05", "0.8 "):
                if needle in text:
                    offenders.append(f"{path.name}: {needle}")
        self.assertEqual(offenders, [], offenders)

    def test_5_no_secret_or_endpoint_is_committed(self):
        code, out = _run("tools/scan_secrets.py")
        self.assertEqual(code, 0, out)
        self.assertIn("ok: 0 finding(s)", out)

    def test_6_the_provenance_ledger_checks_out(self):
        code, out = _run("-m", "govern.provenance", "--check")
        self.assertEqual(code, 0, out)
        self.assertIn("modules covered", out)


class FreezeTests(unittest.TestCase):
    def test_the_corpus_can_be_rebuilt_from_the_factory(self):
        code, out = _run("tools/make_repo.py", "--selftest")
        self.assertEqual(code, 0, out)
        self.assertIn("corpus files match the factory", out)

    def test_the_recordings_can_be_rebuilt_and_replayed_offline(self):
        code, out = _run("-m", "govern.llm", "--selftest")
        self.assertEqual(code, 0, out)
        self.assertIn("6/6 identical", out)

    def test_a_frozen_tree_writes_no_session_data_to_the_repository(self):
        # `runs/` is gitignored, but "no logs written" is a stronger promise:
        # a dry run must not even create the directory.
        with scratch_dir("e2e") as tmp:
            before = {p for p in (ROOT / "runs").rglob("*")} if (ROOT / "runs").exists() else set()
            code, out = _run("-m", "govern.run", "--dry-run")
            after = {p for p in (ROOT / "runs").rglob("*")} if (ROOT / "runs").exists() else set()
        self.assertEqual(code, 0, out)
        self.assertEqual(before, after, "a dry run created files under runs/")

    def test_the_readme_states_its_own_prose_word_count_correctly(self):
        # The first version of the README stated a hand-counted number that was wrong
        # by a factor of four, so the claim is now machine-checked.
        code, out = _run("tools/word_count.py", "--check")
        self.assertEqual(code, 0, out)
        self.assertIn("prose words and has", out)


if __name__ == "__main__":
    unittest.main()
