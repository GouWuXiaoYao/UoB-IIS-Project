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


class DeviceVocabularyTests(unittest.TestCase):
    """The device vocabulary is a config policy with a shape, not a comment."""

    def _write(self, root: Path, **overrides) -> Path:
        import json

        base = json.loads(CONFIG.read_text(encoding="utf-8"))
        base.update(overrides)
        path = root / "config.json"
        path.write_text(json.dumps(base), encoding="utf-8")
        return path

    def test_the_project_config_lists_slug_kinds_and_a_chosen_one(self) -> None:
        cfg = config.load(CONFIG)
        self.assertTrue(cfg.device_kinds)
        self.assertIn(cfg.device, cfg.device_kinds)
        for kind in cfg.device_kinds:
            self.assertRegex(kind, config.DEVICE_KIND_PATTERN)

    def test_a_kind_with_a_space_is_refused(self) -> None:
        with scratch_dir() as root:
            path = self._write(root, device_kinds=["author workstation"], device="author workstation")
            with self.assertRaises(config.ConfigError) as caught:
                config.load(path)
            self.assertIn("slug", str(caught.exception))

    def test_a_hostname_shaped_kind_is_refused(self) -> None:
        with scratch_dir() as root:
            path = self._write(root, device_kinds=["DESKTOP-3F2A9C"], device="DESKTOP-3F2A9C")
            with self.assertRaises(config.ConfigError):
                config.load(path)

    def test_a_device_outside_the_list_is_refused(self) -> None:
        with scratch_dir() as root:
            path = self._write(root, device_kinds=["author-workstation"], device="lab-workstation")
            with self.assertRaises(config.ConfigError) as caught:
                config.load(path)
            self.assertIn("not one of device_kinds", str(caught.exception))

    def test_an_empty_list_is_refused(self) -> None:
        with scratch_dir() as root:
            path = self._write(root, device_kinds=[], device="author-workstation")
            with self.assertRaises(config.ConfigError):
                config.load(path)

    def test_a_repeated_kind_is_refused(self) -> None:
        with scratch_dir() as root:
            path = self._write(root, device_kinds=["author-workstation", "author-workstation"],
                               device="author-workstation")
            with self.assertRaises(config.ConfigError):
                config.load(path)


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

    def test_port_without_a_session_is_a_usage_error(self) -> None:
        # The UI serves exactly one session; without one there is nothing to show.
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run.main(["--port", "8000"])
        self.assertEqual(code, run.EXIT_USAGE)
        self.assertIn("--port needs --session", err.getvalue())


if __name__ == "__main__":
    unittest.main()
