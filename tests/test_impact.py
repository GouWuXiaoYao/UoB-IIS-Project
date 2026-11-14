"""Acceptance tests for M3: the constraint/impact analyser.

The analyser is pure AST work: no model calls, no network, deterministic output.
The corpus labels are authored independently of the analyser (they say what a
human considers to matter), so ``recall == 1.0`` is a real check, not a tautology.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

from _scratch import scratch_dir
from govern import config, impact, tasks

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
CONFIG = config.load(ROOT / "config" / "config.json")

CONTRACT_REPO = {
    "shop/__init__.py": '"""shop package."""\n',
    "shop/state.py": 'TAX_RATE = 0.2\nCACHE = {}\n',
    "shop/core.py": (
        "from shop import state\n\n\n"
        "def total(cents):\n"
        "    return round(cents * (1 + state.TAX_RATE), 2)\n"
    ),
    "shop/reports.py": (
        "from shop import state\n\n\n"
        "def show(cents):\n"
        "    return round(cents * (1 + state.TAX_RATE), 2)\n"
    ),
    "app.py": "from shop import core, reports\n\nprint(core.total(100), reports.show(100))\n",
}

INTERNAL_REPO = {
    "calc/__init__.py": '"""calc package."""\n',
    "calc/arith.py": "def add(a, b):\n    return a + b\n\ndef double(a):\n    return add(a, a)\n",
    "main.py": "from calc import arith\n\nprint(arith.double(2))\n",
}


def _write(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
    return root


class CorpusRecallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.loaded = tasks.load_index(CORPUS)
        cls.scored = [(t, impact.analyze(t.repo, t.intent)) for t in cls.loaded]

    def test_covers_all_six_tasks(self) -> None:
        self.assertEqual(len(self.scored), 6)

    def test_recall_is_perfect_on_every_task(self) -> None:
        for task, result in self.scored:
            with self.subTest(task=task.task_id):
                labels = _labels(task.task_id)
                recall, _precision = impact.recall_precision(result, labels)
                self.assertEqual(recall, CONFIG.impact_recall_min)

    def test_precision_meets_the_configured_floor(self) -> None:
        for task, result in self.scored:
            with self.subTest(task=task.task_id):
                labels = _labels(task.task_id)
                _recall, precision = impact.recall_precision(result, labels)
                self.assertGreaterEqual(precision, CONFIG.impact_precision_min)

    def test_categories_stay_inside_the_enum(self) -> None:
        for _task, result in self.scored:
            for item in result.items:
                self.assertIn(item.category, impact.CATEGORIES)

    def test_items_are_traceable(self) -> None:
        for _task, result in self.scored:
            ids = [item.item_id for item in result.items]
            self.assertEqual(len(ids), len(set(ids)), "item ids must be unique")
            for item in result.items:
                self.assertTrue(item.symbol, "every item needs a symbol")
                self.assertTrue(item.files, "every item needs at least one file")
                self.assertTrue(item.detail, "every item needs a detail line")


class NotMemorisedTests(unittest.TestCase):
    """Negative control: the analyser must react to code, not to the labels."""

    def test_an_extra_reader_adds_a_contract_and_costs_precision(self) -> None:
        task = tasks.load_index(CORPUS)[0]
        labels = _labels(task.task_id)
        with scratch_dir() as tmp:
            repo = tmp / "repo"
            shutil.copytree(task.repo, repo)
            (repo / "billing" / "extra.py").write_text(
                "from billing import state\n\n\ndef gross(cents):\n"
                "    return round(cents * (1 + state.TAX_RATE), 2)\n",
                encoding="utf-8",
                newline="",
            )
            result = impact.analyze(repo, task.intent)
        contracts = result.of("cross_module_contract")
        self.assertIn("billing.core->billing.extra", {item.symbol for item in contracts})
        _recall, precision = impact.recall_precision(result, labels)
        self.assertLess(precision, 1.0, "an unlabelled contract must lower precision")


class DeterminismTests(unittest.TestCase):
    def test_same_input_same_hash(self) -> None:
        task = tasks.load_index(CORPUS)[0]
        first = impact.analyze(task.repo, task.intent)
        second = impact.analyze(task.repo, task.intent)
        self.assertEqual(impact.impact_hash(first), impact.impact_hash(second))

    def test_hash_is_stable_across_processes(self) -> None:
        """A hash that depends on dict/set iteration order would fail here."""
        code = (
            "from pathlib import Path;"
            "from govern import impact;"
            "print(impact.impact_hash(impact.analyze(Path('corpus/T-L03a/repo'), 'x')))"
        )
        digests = set()
        for _ in range(2):
            proc = subprocess.run(
                [sys.executable, "-c", code],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            digests.add(proc.stdout.strip())
        self.assertEqual(len(digests), 1)

    def test_hash_ignores_intent_wording(self) -> None:
        task = tasks.load_index(CORPUS)[0]
        a = impact.analyze(task.repo, task.intent)
        b = impact.analyze(task.repo, "completely different wording")
        self.assertEqual(impact.impact_hash(a), impact.impact_hash(b))


class RiskLevelTests(unittest.TestCase):
    def test_contract_change_is_high_risk(self) -> None:
        with scratch_dir() as tmp:
            repo = _write(tmp / "repo", CONTRACT_REPO)
            result = impact.analyze(repo, "move money to integer minor units")
        self.assertEqual(impact.risk_level(result), "high")

    def test_internal_only_change_is_low_risk(self) -> None:
        with scratch_dir() as tmp:
            repo = _write(tmp / "repo", INTERNAL_REPO)
            result = impact.analyze(repo, "rename a local helper")
        self.assertEqual(impact.risk_level(result), "low")

    def test_the_two_cases_differ(self) -> None:
        with scratch_dir() as tmp:
            high = impact.analyze(_write(tmp / "a", CONTRACT_REPO), "x")
            low = impact.analyze(_write(tmp / "b", INTERNAL_REPO), "x")
        self.assertNotEqual(impact.risk_level(high), impact.risk_level(low))


class RobustnessTests(unittest.TestCase):
    def test_empty_repository_returns_an_empty_set(self) -> None:
        with scratch_dir() as tmp:
            (tmp / "repo").mkdir()
            result = impact.analyze(tmp / "repo", "nothing here")
        self.assertEqual(result.items, ())
        self.assertEqual(impact.risk_level(result), "low")

    def test_syntax_error_is_reported_not_raised(self) -> None:
        with scratch_dir() as tmp:
            repo = _write(tmp / "repo", {"pkg/__init__.py": "", "pkg/broken.py": "def oops(:\n"})
            result = impact.analyze(repo, "touch the broken module")
        categories = [item.category for item in result.items]
        self.assertIn("other", categories)
        self.assertTrue(any("syntax" in item.detail.lower() for item in result.items))

    def test_single_file_repository_is_fine(self) -> None:
        with scratch_dir() as tmp:
            repo = _write(tmp / "repo", {"solo.py": "def one():\n    return 1\n"})
            result = impact.analyze(repo, "single file")
        self.assertEqual([item.category for item in result.items], [])

    def test_missing_repository_returns_an_other_item(self) -> None:
        with scratch_dir() as tmp:
            result = impact.analyze(tmp / "does-not-exist", "x")
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].category, "other")


class PerformanceTests(unittest.TestCase):
    def test_analysis_is_under_two_seconds_on_the_largest_task(self) -> None:
        task = [t for t in tasks.load_index(CORPUS) if t.stratum == "H"][0]
        start = time.monotonic()
        for _ in range(5):
            impact.analyze(task.repo, task.intent)
        elapsed = (time.monotonic() - start) / 5
        self.assertLess(elapsed, 2.0, f"mean analysis time was {elapsed:.3f}s")


class CliTests(unittest.TestCase):
    def test_selftest_reports_recall_and_precision(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "govern.impact", "--selftest"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("recall=1.00", proc.stdout)
        self.assertIn("on 6 tasks", proc.stdout)


def _labels(task_id: str) -> dict:
    import json  # noqa: PLC0415

    return json.loads((CORPUS / task_id / "impact_labels.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
