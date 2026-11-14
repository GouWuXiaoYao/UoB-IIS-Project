"""Acceptance tests for the seed corpus: every task must be gradeable, matched and leak-free."""

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
EXPECTED_IDS = ["T-L01a", "T-L01b", "T-L02a", "T-L02b", "T-L03a", "T-L03b"]
EXPECTED_PAIRS = {"PAIR-01": "L", "PAIR-02": "M", "PAIR-03": "H"}


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _labels(task_id: str) -> dict:
    return json.loads((CORPUS / task_id / "impact_labels.json").read_text(encoding="utf-8"))


class IndexTests(unittest.TestCase):
    def test_index_holds_three_pairs(self) -> None:
        loaded = tasks.load_index(CORPUS)
        self.assertEqual([t.task_id for t in loaded], EXPECTED_IDS)
        self.assertEqual({t.pair_id for t in loaded}, set(EXPECTED_PAIRS))

    def test_each_pair_has_two_tasks_of_one_stratum(self) -> None:
        loaded = tasks.load_index(CORPUS)
        for pair_id, stratum in EXPECTED_PAIRS.items():
            with self.subTest(pair=pair_id):
                members = [t for t in loaded if t.pair_id == pair_id]
                self.assertEqual(len(members), 2)
                self.assertEqual({t.stratum for t in members}, {stratum})

    def test_strata_cover_low_medium_high(self) -> None:
        loaded = tasks.load_index(CORPUS)
        self.assertEqual(sorted({t.stratum for t in loaded}), ["H", "L", "M"])

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
    def test_each_task_has_global_state_and_contract(self) -> None:
        for task_id in EXPECTED_IDS:
            with self.subTest(task=task_id):
                labels = _labels(task_id)
                self.assertGreaterEqual(len(labels["global_vars"]), 1)
                self.assertGreaterEqual(len(labels["cross_module_contracts"]), 1)

    def test_every_pair_is_matched_within_tolerance(self) -> None:
        tolerance = config.load(ROOT / "config" / "config.json").pair_tolerance
        members: dict[str, list[dict]] = {}
        for task_id in EXPECTED_IDS:
            labels = _labels(task_id)
            members.setdefault(labels["pair_id"], []).append(labels)
        self.assertEqual(len(members), 3)
        for pair_id, pair in members.items():
            with self.subTest(pair=pair_id):
                self.assertEqual(len(pair), 2)
                for key in PAIR_KEYS:
                    high, low = max(p[key] for p in pair), min(p[key] for p in pair)
                    self.assertGreater(low, 0, f"{pair_id}:{key} must not be zero")
                    self.assertLessEqual((high - low) / high, tolerance)

    def test_declared_file_count_matches_patch(self) -> None:
        for task_id in EXPECTED_IDS:
            with self.subTest(task=task_id):
                labels = _labels(task_id)
                patch_text = (CORPUS / task_id / "gold.patch").read_text(encoding="utf-8")
                self.assertEqual(len(corpus.changed_files(patch_text)), labels["files_to_change"])

    def test_higher_strata_touch_more_files(self) -> None:
        counts = {task_id: _labels(task_id)["files_to_change"] for task_id in EXPECTED_IDS}
        self.assertLess(counts["T-L01a"], counts["T-L02a"])
        self.assertLess(counts["T-L02a"], counts["T-L03a"])


class CliTests(unittest.TestCase):
    def test_check_command_prints_summary(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "govern.corpus", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("ok: 6 tasks, gold 6/6, pairs 3/3 within 20%", proc.stdout)


class FactoryTests(unittest.TestCase):
    def test_factory_is_deterministic(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            import make_repo  # noqa: PLC0415
        finally:
            sys.path.pop(0)
        first = make_repo.build_corpus()
        second = make_repo.build_corpus()
        self.assertEqual(first, second)
        self.assertEqual(len([n for n in first if n.endswith("gold.patch")]), 6)

    def test_committed_corpus_matches_factory(self) -> None:
        proc = subprocess.run(
            [sys.executable, "tools/make_repo.py", "--selftest"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("corpus files match the factory", proc.stdout)


if __name__ == "__main__":
    unittest.main()
