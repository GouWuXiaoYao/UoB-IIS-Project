"""The hidden-suite runner (SPEC M8 acceptance 4: sandboxed, timed out).

These tests exist because the runner is the only place where the project
executes code it did not write in the current process: a suite that hangs, a
suite that explodes at import time and an empty suite must all be reported, not
inherited by the session.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from govern import hidden  # noqa: E402
from tests._scratch import scratch_dir  # noqa: E402


def write(directory: Path, name: str, body: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body, encoding="utf-8")


class PassingSuiteTests(unittest.TestCase):
    def test_a_passing_suite_reports_zero_and_the_test_count(self) -> None:
        with scratch_dir() as tmp:
            suite = tmp / "suite"
            write(suite, "test_ok.py", "def test_a():\n    assert 1 + 1 == 2\n\ndef test_b():\n    assert True\n")
            code, failures, n = hidden.run(tmp, suite, 30)
            self.assertEqual((code, failures, n), (0, [], 2))

    def test_every_test_file_in_the_directory_is_run(self) -> None:
        with scratch_dir() as tmp:
            suite = tmp / "suite"
            write(suite, "test_one.py", "def test_a():\n    assert True\n")
            write(suite, "test_two.py", "def test_b():\n    assert True\n")
            self.assertEqual(hidden.run(tmp, suite, 30), (0, [], 2))


class FailingSuiteTests(unittest.TestCase):
    def test_a_failing_assertion_names_the_file_and_the_test(self) -> None:
        with scratch_dir() as tmp:
            suite = tmp / "suite"
            write(suite, "test_bad.py", "def test_boom():\n    assert False, 'boom'\n")
            code, failures, n = hidden.run(tmp, suite, 30)
            self.assertEqual((code, n), (1, 1))
            self.assertIn("test_bad.py::test_boom", failures[0])
            self.assertIn("boom", failures[0])

    def test_a_module_that_explodes_on_import_is_a_failure_not_a_crash(self) -> None:
        with scratch_dir() as tmp:
            suite = tmp / "suite"
            write(suite, "test_import.py", "raise RuntimeError('no import for you')\n")
            code, failures, n = hidden.run(tmp, suite, 30)
            self.assertEqual(code, 1)
            self.assertIn("<import>", failures[0])

    def test_a_suite_that_calls_sys_exit_is_reported(self) -> None:
        with scratch_dir() as tmp:
            suite = tmp / "suite"
            write(suite, "test_exit.py", "import sys\n\ndef test_quit():\n    sys.exit(3)\n")
            code, failures, n = hidden.run(tmp, suite, 30)
            self.assertEqual(code, 1)
            self.assertIn("SystemExit", failures[0])


class IsolationTests(unittest.TestCase):
    def test_a_hanging_suite_is_killed_within_a_budget(self) -> None:
        with scratch_dir() as tmp:
            suite = tmp / "suite"
            write(suite, "test_hang.py", "def test_hang():\n    while True:\n        pass\n")
            started = time.monotonic()
            code, failures, n = hidden.run(tmp, suite, 2)
            elapsed = time.monotonic() - started
            self.assertEqual(code, 2)
            self.assertTrue(any("timeout" in f for f in failures), failures)
            self.assertLess(elapsed, 15)

    def test_an_empty_suite_is_an_error_not_a_pass(self) -> None:
        with scratch_dir() as tmp:
            suite = tmp / "suite"
            suite.mkdir(parents=True)
            code, failures, n = hidden.run(tmp, suite, 30)
            self.assertEqual(code, 2)
            self.assertIn("no test_* functions", failures[0])

    def test_the_suite_imports_from_the_candidate_repository(self) -> None:
        with scratch_dir() as tmp:
            (tmp / "pkg").mkdir()
            (tmp / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (tmp / "pkg" / "core.py").write_text("VALUE = 7\n", encoding="utf-8")
            suite = tmp / "suite"
            write(
                suite,
                "test_core.py",
                "from pkg.core import VALUE\n\ndef test_value():\n    assert VALUE == 7\n",
            )
            self.assertEqual(hidden.run(tmp, suite, 30), (0, [], 1))

    def test_a_stdout_writing_suite_does_not_confuse_the_report(self) -> None:
        with scratch_dir() as tmp:
            suite = tmp / "suite"
            write(
                suite,
                "test_noisy.py",
                "def test_noisy():\n    print('noise on stdout')\n    assert True\n",
            )
            self.assertEqual(hidden.run(tmp, suite, 30), (0, [], 1))


class CliTests(unittest.TestCase):
    def test_selftest_reports_the_runner(self) -> None:
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = hidden.main(["--selftest"])
        self.assertEqual(code, 0, buffer.getvalue())
        self.assertIn("child interpreter", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
