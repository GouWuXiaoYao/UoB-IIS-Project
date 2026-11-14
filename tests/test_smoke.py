"""M0 smoke tests: the project skeleton must be importable and self-checking."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from govern import config, run, tasks

from _scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "config.json"


class ConfigTests(unittest.TestCase):
    def test_loads_project_config(self) -> None:
        cfg = config.load(CONFIG)
        self.assertEqual(cfg.conditions, ("C0", "C1"))
        self.assertEqual(cfg.seed, 42)
        self.assertAlmostEqual(cfg.temperature, 0.2)
        self.assertGreater(cfg.n_participants, 0)

    def test_seed_is_deterministic_across_loads(self) -> None:
        self.assertEqual(config.load(CONFIG), config.load(CONFIG))

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(config.ConfigError):
            config.load(ROOT / "config" / "does-not-exist.json")


class CorpusTests(unittest.TestCase):
    def test_empty_index_yields_no_tasks(self) -> None:
        with scratch_dir() as root:
            (root / "index.json").write_text('{"tasks": []}', encoding="utf-8")
            self.assertEqual(tasks.load_index(root), [])

    def test_shipped_index_loads(self) -> None:
        loaded = tasks.load_index(ROOT / "corpus")
        self.assertGreaterEqual(len(loaded), 2)


class RunTests(unittest.TestCase):
    def test_selftest_prints_counts(self) -> None:
        expected = f"ok: {len(tasks.load_index(ROOT / 'corpus'))} tasks, 6 cards"
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run.selftest(CONFIG)
        self.assertEqual(code, run.EXIT_OK)
        self.assertEqual(buf.getvalue().strip(), expected)

    def test_dry_run_is_offline_and_writes_nothing(self) -> None:
        before = sorted(p.name for p in ROOT.iterdir())
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run.dry_run(CONFIG)
        self.assertEqual(code, run.EXIT_OK)
        self.assertIn("no network used", buf.getvalue())
        self.assertEqual(before, sorted(p.name for p in ROOT.iterdir()))

    def test_unimplemented_flag_exits_non_zero(self) -> None:
        # The web UI is M9; until then --port must fail loudly rather than pretend.
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run.main(["--port", "8000"])
        self.assertEqual(code, run.EXIT_NOT_READY)
        self.assertIn("not implemented yet", err.getvalue())


if __name__ == "__main__":
    unittest.main()
