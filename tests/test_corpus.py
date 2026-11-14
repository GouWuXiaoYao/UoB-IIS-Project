"""Acceptance tests for M1: the seed corpus must be gradeable and leak-free."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from govern import config, corpus, tasks

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
PAIR_KEYS = ("files_to_change", "functions_to_change", "hidden_tests")


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


class IndexTests(unittest.TestCase):
    def test_index_holds_one_pair(self) -> None:
        loaded = tasks.load_index(CORPUS)
        self.assertEqual([t.task_id for t in loaded], ["T-L01a", "T-L01b"])
        self.assertEqual({t.pair_id for t in loaded}, {"PAIR-01"})
        self.assertEqual({t.stratum for t in loaded}, {"L"})

    def test_every_task_directory_is_complete(self) -> None:
        for task in tasks.load_index(CORPUS):
            with self.subTest(task=task.task_id):
                self.assertTrue(task.repo.is_dir())
                self.assertTrue(task.gold_patch.is_file())
                self.assertTrue(task.hidden_tests.is_dir())
                self.assertTrue((CORPUS / task.task_id / "intent.md").is_file())
                self.assertTrue((CORPUS / task.task_id / "impact_labels.json").is_file())


class CheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.digest_before = _tree_digest(CORPUS)
        cls.checks = corpus.check_all(CORPUS)

    def test_check_all_covers_every_task(self) -> None:
        self.assertEqual(len(self.checks), len(tasks.load_index(CORPUS)))

    def test_gold_patch_turns_hidden_tests_green(self) -> None:
        for check in self.checks:
            with self.subTest(task=check.task_id):
                self.assertTrue(check.gold_green, msg=check.detail)

    def test_baseline_fails_for_refactor_reason(self) -> None:
        for check in self.checks:
            with self.subTest(task=check.task_id):
                reason = check.baseline_fail_reason
                self.assertTrue(reason, "baseline must be recorded, not skipped")
                for forbidden in ("ModuleNotFoundError", "ImportError", "no tests ran", "ERROR"):
                    self.assertNotIn(forbidden, reason)

    def test_labels_are_complete(self) -> None:
        for check in self.checks:
            with self.subTest(task=check.task_id):
                self.assertTrue(check.labels_ok, msg=check.detail)

    def test_repositories_do_not_leak_the_answer(self) -> None:
        for check in self.checks:
            with self.subTest(task=check.task_id):
                self.assertTrue(check.leak_free, msg=check.detail)

    def test_check_all_is_read_only(self) -> None:
        self.assertEqual(self.digest_before, _tree_digest(CORPUS))


class LabelTests(unittest.TestCase):
    def _labels(self, task_id: str) -> dict:
        return json.loads((CORPUS / task_id / "impact_labels.json").read_text(encoding="utf-8"))

    def test_each_task_has_global_state_and_contract(self) -> None:
        for task_id in ("T-L01a", "T-L01b"):
            with self.subTest(task=task_id):
                labels = self._labels(task_id)
                self.assertGreaterEqual(len(labels["global_vars"]), 1)
                self.assertGreaterEqual(len(labels["cross_module_contracts"]), 1)

    def test_pair_is_matched_within_twenty_percent(self) -> None:
        tolerance = config.load(ROOT / "config" / "config.json").pair_tolerance
        a, b = self._labels("T-L01a"), self._labels("T-L01b")
        for key in PAIR_KEYS:
            with self.subTest(metric=key):
                high, low = max(a[key], b[key]), min(a[key], b[key])
                self.assertGreater(low, 0)
                self.assertLessEqual((high - low) / high, tolerance)

    def test_declared_file_count_matches_patch(self) -> None:
        for task_id in ("T-L01a", "T-L01b"):
            with self.subTest(task=task_id):
                labels = self._labels(task_id)
                patch = (CORPUS / task_id / "gold.patch").read_text(encoding="utf-8")
                self.assertEqual(len(corpus.changed_files(patch)), labels["files_to_change"])


class CliTests(unittest.TestCase):
    def test_check_command_prints_summary(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "govern.corpus", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("ok: 2 tasks, gold 2/2, labels 2/2", proc.stdout)


if __name__ == "__main__":
    unittest.main()
