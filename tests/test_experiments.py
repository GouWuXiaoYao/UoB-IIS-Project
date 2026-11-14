"""Tests for the experiment orchestration layer in ``experiments/``.

The layer exists so that a run is described by a file rather than by a command
line, and so that a run is reproducible: the plan, the model parameters and the
task order all land in the run directory before the first session starts.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from experiments import metrics, runner, spec
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "conditions.yaml"


def _spec_dict() -> dict:
    return {
        "version": 1,
        "run_id": "E-UNIT",
        "participants": ["P01"],
        "conditions": {"baseline": {"condition": "C0"}, "governance": {"condition": "C1"}},
        "pairs": ["PAIR-01"],
        "concurrency": {"max_parallel": 2},
    }


class YamlTests(unittest.TestCase):
    def test_nested_mappings_and_scalars(self):
        text = "a:\n  b: 1\n  c: two\nd: true\n"
        self.assertEqual(spec.parse_yaml(text), {"a": {"b": 1, "c": "two"}, "d": True})

    def test_block_sequences(self):
        text = "items:\n  - one\n  - two\n"
        self.assertEqual(spec.parse_yaml(text), {"items": ["one", "two"]})

    def test_inline_sequences_of_scalars(self):
        self.assertEqual(spec.parse_yaml("pairs: [PAIR-01, PAIR-02]\n"), {"pairs": ["PAIR-01", "PAIR-02"]})

    def test_comments_and_quoted_strings_are_handled(self):
        text = '# top\nrun_id: "E 1"  # trailing\n'
        self.assertEqual(spec.parse_yaml(text), {"run_id": "E 1"})

    def test_a_tab_indent_is_rejected_rather_than_guessed(self):
        with self.assertRaises(spec.SpecError):
            spec.parse_yaml("a:\n\tb: 1\n")

    def test_json_is_accepted_directly(self):
        # JSON is a subset of YAML; accepting it removes a parser dependency.
        self.assertEqual(spec.parse_yaml('{"a": 1}'), {"a": 1})


class SpecTests(unittest.TestCase):
    def test_the_shipped_conditions_file_loads(self):
        loaded = spec.load(CONFIG)
        self.assertEqual(loaded.version, 1)
        self.assertEqual(set(loaded.conditions), {"baseline", "governance"})
        self.assertGreaterEqual(loaded.max_parallel, 1)

    def test_conditions_map_to_the_two_condition_codes(self):
        loaded = spec.load(CONFIG)
        self.assertEqual(loaded.conditions["baseline"], "C0")
        self.assertEqual(loaded.conditions["governance"], "C1")

    def test_a_missing_baseline_is_rejected(self):
        raw = _spec_dict()
        del raw["conditions"]["baseline"]
        with self.assertRaises(spec.SpecError):
            spec.validate(raw)

    def test_an_unknown_condition_code_is_rejected(self):
        raw = _spec_dict()
        raw["conditions"]["baseline"]["condition"] = "C9"
        with self.assertRaises(spec.SpecError):
            spec.validate(raw)

    def test_cells_cover_every_condition_and_task_once(self):
        loaded = spec.load(CONFIG)
        task_list = spec.load_tasks(loaded)
        cells = loaded.cells(task_list)
        self.assertEqual(len(cells), len(loaded.conditions) * len(task_list))
        keys = {(cell.name, cell.task_id) for cell in cells}
        self.assertEqual(len(keys), len(cells), "a cell must not be scheduled twice")

    def test_cell_order_is_deterministic(self):
        loaded = spec.load(CONFIG)
        task_list = spec.load_tasks(loaded)
        first = [cell.key for cell in loaded.cells(task_list)]
        second = [cell.key for cell in loaded.cells(task_list)]
        self.assertEqual(first, second)


class RunnerTests(unittest.TestCase):
    def _small(self) -> spec.Spec:
        raw = _spec_dict()
        raw["pairs"] = ["PAIR-01"]
        return spec.validate(raw)

    def test_a_run_writes_the_snapshot_logs_and_metrics(self):
        small = self._small()
        with scratch_dir("exp") as tmp:
            report = runner.execute(small, runs_root=tmp, workers=1)
            run_dir = tmp / "E-UNIT"
            self.assertTrue((run_dir / "config.snapshot.json").is_file())
            self.assertTrue((run_dir / "manifest.json").is_file())
            self.assertTrue((run_dir / "metrics.json").is_file())
            logs = list((run_dir / "logs").rglob("*.jsonl"))
            self.assertEqual(len(logs), report["n_total"])
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            for key in ("model_id", "model_temperature", "seed", "task_order"):
                self.assertIn(key, manifest)

    def test_resume_skips_sessions_that_already_ended(self):
        small = self._small()
        with scratch_dir("exp") as tmp:
            first = runner.execute(small, runs_root=tmp, workers=1)
            second = runner.execute(small, runs_root=tmp, workers=1, resume=True)
            self.assertEqual(first["n_ran"], first["n_total"])
            self.assertEqual(second["n_ran"], 0)
            self.assertEqual(second["n_skipped"], second["n_total"])

    def test_a_failing_cell_does_not_stop_the_batch(self):
        small = self._small()
        with scratch_dir("exp") as tmp:
            report = runner.execute(
                small, runs_root=tmp, workers=1, simulate=lambda sess, consent: _boom(sess)
            )
            self.assertEqual(report["n_failed"], report["n_total"])
            failures = (tmp / "E-UNIT" / "failures.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(failures), report["n_total"])
            record = json.loads(failures[0])
            for key in ("run_id", "cell", "task_id", "condition", "error", "message"):
                self.assertIn(key, record)

    def test_metrics_are_recomputed_from_the_logs_on_disk(self):
        small = self._small()
        with scratch_dir("exp") as tmp:
            runner.execute(small, runs_root=tmp, workers=1)
            run_dir = tmp / "E-UNIT"
            on_disk = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
            again = metrics.rebuild(run_dir)
            self.assertEqual(on_disk["conditions"], again["conditions"])


def _boom(sess):
    raise RuntimeError("designed failure for the isolation test")


class MetricsTests(unittest.TestCase):
    def _session(self, **overrides) -> dict:
        base = {
            "session_id": "S-1",
            "participant": "P01",
            "condition": "C1",
            "task_id": "T-L01a",
            "pair_id": "PAIR-01",
            "events": [
                {"event_type": "card_item_toggle", "dwell_ms": 100},
                {"event_type": "gate_decision", "confirmed": True, "blocked": False, "n_required": 5, "n_confirmed": 5},
                {"event_type": "suggestion_action", "suggestion_id": "S1", "action": "accept",
                 "review_dwell_ms": 1200, "accepted_after_gate": True},
                {"event_type": "task_end", "tests_pass": True, "debt_delta": -2.0, "elapsed_ms": 5000},
                {"event_type": "session_end", "completed_all": True},
            ],
        }
        base.update(overrides)
        return base

    def test_escape_defect_rate_counts_failed_hidden_suites(self):
        good = self._session()
        bad = self._session(session_id="S-2")
        bad["events"][3]["tests_pass"] = False
        summary = metrics.summarise([good, bad], tau_review_ms=3000, mech_dwell_ms=800)
        self.assertEqual(summary["conditions"]["C1"]["n_sessions"], 2)
        self.assertEqual(summary["conditions"]["C1"]["escape_defect_rate"], 0.5)

    def test_oti_counts_accepts_below_the_review_threshold(self):
        quick = self._session()
        slow = self._session(session_id="S-2")
        slow["events"][2]["review_dwell_ms"] = 5000
        summary = metrics.summarise([quick, slow], tau_review_ms=3000, mech_dwell_ms=800)
        self.assertEqual(summary["conditions"]["C1"]["blind_accepts"], 1)
        self.assertAlmostEqual(summary["conditions"]["C1"]["oti"], 0.5)

    def test_an_explanation_opened_means_the_accept_is_not_blind(self):
        opened = self._session()
        opened["events"].insert(2, {"event_type": "explanation_open", "suggestion_id": "S1", "layer": "L1", "dwell_ms": 400})
        summary = metrics.summarise([opened], tau_review_ms=3000, mech_dwell_ms=800)
        self.assertEqual(summary["conditions"]["C1"]["blind_accepts"], 0)

    def test_mechanical_confirmation_is_counted_from_the_toggle_dwells(self):
        fast = self._session()
        summary = metrics.summarise([fast], tau_review_ms=3000, mech_dwell_ms=800)
        self.assertEqual(summary["conditions"]["C1"]["mechanical_confirmations"], 1)
        slow = self._session(session_id="S-2")
        slow["events"][0]["dwell_ms"] = 4000
        summary = metrics.summarise([slow], tau_review_ms=3000, mech_dwell_ms=800)
        self.assertEqual(summary["conditions"]["C1"]["mechanical_confirmations"], 0)

    def test_pair_level_comparison_lists_both_conditions(self):
        a = self._session()
        b = self._session(session_id="S-2", condition="C0")
        summary = metrics.summarise([a, b], tau_review_ms=3000, mech_dwell_ms=800)
        self.assertEqual(set(summary["pairs"][0]), {"pair_id", "C0", "C1"})


class CliTests(unittest.TestCase):
    def test_dry_run_plans_without_writing(self):
        with scratch_dir("exp") as tmp:
            code, out = _call("--config", str(CONFIG), "--runs-root", str(tmp), "--dry-run")
            self.assertEqual(code, 0, out)
            self.assertIn("dry run", out)
            self.assertIn("sessions", out)
            self.assertEqual(list(tmp.rglob("*.jsonl")), [])

    def test_a_missing_config_is_a_usage_error(self):
        code, out = _call("--config", str(ROOT / "nope.yaml"), "--dry-run")
        self.assertEqual(code, 2, out)

    def test_a_real_run_prints_a_table_and_writes_metrics(self):
        with scratch_dir("exp") as tmp:
            sub = tmp / "small.yaml"
            sub.write_text(
                "version: 1\nrun_id: E-CLI\nparticipants: [P01]\n"
                "conditions:\n  baseline:\n    condition: C0\n  governance:\n    condition: C1\n"
                "pairs: [PAIR-01]\nconcurrency:\n  max_parallel: 2\n",
                encoding="utf-8",
            )
            code, out = _call("--config", str(sub), "--runs-root", str(tmp))
            self.assertEqual(code, 0, out)
            self.assertIn("| condition |", out)
            self.assertTrue((tmp / "E-CLI" / "metrics.json").is_file())


def _call(*argv: str) -> tuple[int, str]:
    import contextlib
    import io

    from experiments import run as cli

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = cli.main(list(argv))
    return code, buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
