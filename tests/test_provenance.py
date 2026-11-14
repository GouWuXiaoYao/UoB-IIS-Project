"""Acceptance tests for the provenance ledger (SPEC M11 / PLAN milestone M10).

The ledger exists to make "original / reused / assisted" checkable instead of
rhetorical, so these tests are deliberately about the *规则* and not just about
the happy path: only-original ledgers, assisted rows with no evidence, reused
rows pointing nowhere, and rows of the wrong shape all have to be caught.
"""

from __future__ import annotations

import io
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from govern import provenance
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "PROVENANCE.md"
HEADER = (
    "| item_id | module | origin | source | decision | check | commit |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _table(*rows: str) -> str:
    return HEADER + "".join(row + "\n" for row in rows)


def _row(
    item_id: str = "P-001",
    module: str = "M1",
    origin: str = "original",
    source: str = "-",
    decision: str = "chose the factory because the corpus must be rebuildable",
    check: str = "make_repo --selftest",
    commit: str = "b10face",
) -> str:
    return f"| {item_id} | {module} | {origin} | {source} | {decision} | {check} | {commit} |"


def _three_origin_ledger(*extra: str, modules: tuple[str, ...] = ("M1", "M4", "M5", "M6", "M7")) -> str:
    """A ledger that satisfies every rule, so a test can break exactly one."""
    rows = [
        _row("P-001", modules[0], "original"),
        _row("P-002", modules[1], "reused", source="README.md"),
        _row("P-003", modules[2], "assisted"),
        _row("P-004", modules[3], "original"),
        _row("P-005", modules[4], "original"),
    ]
    rows.extend(_row(f"R-{n:03d}", module, "original") for n, module in enumerate(provenance.MODULES, start=100) if module not in modules)
    rows.extend(extra)
    return _table(*rows)


def _write(tmp: Path, text: str, name: str = "PROVENANCE.md") -> Path:
    path = tmp / name
    path.write_text(text, encoding="utf-8")
    return path


def _call(*argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        code = provenance.main(list(argv))
    return code, buffer.getvalue()


class ParseTests(unittest.TestCase):
    def test_the_shipped_ledger_parses_into_rows(self):
        rows = provenance.parse(LEDGER)
        self.assertGreaterEqual(len(rows), 12)

    def test_the_header_and_separator_are_not_rows(self):
        rows = provenance.parse(_write_text(_three_origin_ledger()))
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows[0].item_id, "P-001")

    def test_cells_are_trimmed(self):
        rows = provenance.parse(_write_text(_table(_row(item_id="  P-009  ", module=" M1 "))))
        self.assertEqual(rows[0].item_id, "P-009")
        self.assertEqual(rows[0].module, "M1")

    def test_preamble_and_blank_lines_are_ignored(self):
        text = "# Ledger\n\nSome prose about why this file exists.\n\n" + _three_origin_ledger()
        rows = provenance.parse(_write_text(text))
        self.assertEqual(len(rows), 11)

    def test_a_row_with_the_wrong_number_of_cells_is_an_error(self):
        text = HEADER + "| P-001 | M1 | original |\n"
        with self.assertRaises(provenance.LedgerError) as caught:
            provenance.parse(_write_text(text))
        self.assertIn("7 cells", str(caught.exception))

    def test_a_ledger_with_no_rows_is_an_error(self):
        with self.assertRaises(provenance.LedgerError):
            provenance.parse(_write_text("# nothing here\n"))


class CheckTests(unittest.TestCase):
    def _problems(self, text: str) -> list[str]:
        return provenance.check(provenance.parse(_write_text(text)), root=ROOT)

    def test_the_shipped_ledger_passes(self):
        self.assertEqual(provenance.check(provenance.parse(LEDGER), root=ROOT), [])

    def test_the_shipped_ledger_covers_every_module(self):
        rows = provenance.parse(LEDGER)
        covered = {row.module for row in rows}
        for module in provenance.MODULES:
            self.assertIn(module, covered, f"{module} has no provenance row")

    def test_an_external_source_is_allowed_when_the_decision_says_why(self):
        text = _three_origin_ledger(
            _row("P-030", "M8", "reused", source="external:参考代码库/tools.py",
                 decision="course lab material, deliberately not redistributed")
        )
        self.assertEqual(self._problems(text), [])

    def test_an_external_source_without_a_decision_is_reported(self):
        text = _three_origin_ledger(
            _row("P-031", "M8", "reused", source="external:参考代码库/tools.py", decision="")
        )
        problems = self._problems(text)
        self.assertTrue(any("P-031" in p and "external" in p for p in problems), problems)

    def test_a_missing_reused_source_is_still_reported(self):
        text = _three_origin_ledger(
            _row("P-032", "M8", "reused", source="govern/does-not-exist.py")
        )
        problems = self._problems(text)
        self.assertTrue(any("P-032" in p and "does not exist" in p for p in problems), problems)

    def test_a_missing_must_module_is_reported(self):
        rows = [_row(f"R-{n:03d}", module, "original") for n, module in enumerate(provenance.MODULES, 1) if module != "M7"]
        rows.append(_row("P-900", "M1", "reused", source="README.md"))
        rows.append(_row("P-901", "M1", "assisted"))
        problems = self._problems(_table(*rows))
        self.assertTrue(any("M7" in problem for problem in problems), problems)

    def test_a_ledger_with_only_original_rows_is_reported(self):
        text = _table(
            *[_row(f"P-00{i}", module, "original") for i, module in enumerate(("M1", "M4", "M5", "M6", "M7"), 1)]
        )
        problems = self._problems(text)
        self.assertTrue(any("reused" in problem for problem in problems), problems)
        self.assertTrue(any("assisted" in problem for problem in problems), problems)

    def test_an_assisted_row_without_a_check_is_reported(self):
        text = _three_origin_ledger(_row("P-010", "M7", "assisted", check=""))
        problems = self._problems(text)
        self.assertTrue(any("P-010" in problem and "check" in problem for problem in problems), problems)

    def test_an_assisted_row_without_a_decision_is_reported(self):
        text = _three_origin_ledger(_row("P-011", "M6", "assisted", decision=""))
        problems = self._problems(text)
        self.assertTrue(any("P-011" in problem and "decision" in problem for problem in problems), problems)

    def test_a_reused_row_pointing_at_a_missing_path_is_reported(self):
        text = _three_origin_ledger(
            _row("P-012", "M5", "reused", source="docs/does_not_exist.py")
        )
        problems = self._problems(text)
        self.assertTrue(any("P-012" in problem for problem in problems), problems)

    def test_a_reused_row_may_point_at_a_directory(self):
        # A directory that every checkout has; 参考代码库/ is deliberately not tracked.
        text = _three_origin_ledger(_row("P-013", "M5", "reused", source="docs"))
        self.assertEqual(self._problems(text), [])

    def test_an_unknown_origin_is_reported(self):
        text = _three_origin_ledger(_row("P-014", "M5", "generated"))
        problems = self._problems(text)
        self.assertTrue(any("P-014" in problem and "origin" in problem for problem in problems), problems)

    def test_an_unknown_module_is_reported(self):
        text = _three_origin_ledger(_row("P-015", "M99"))
        problems = self._problems(text)
        self.assertTrue(any("P-015" in problem and "module" in problem for problem in problems), problems)

    def test_a_dash_does_not_count_as_evidence(self):
        # A markdown table says "empty" with a dash, so a cosmetic dash must not
        # pass for a written decision or check.
        text = _three_origin_ledger(_row("P-016", "M6", "assisted", decision="-", check="-"))
        problems = self._problems(text)
        self.assertTrue(any("P-016" in problem and "decision" in problem for problem in problems), problems)
        self.assertTrue(any("P-016" in problem and "check" in problem for problem in problems), problems)

    def test_a_duplicate_item_id_is_reported(self):
        text = _three_origin_ledger(_row("P-001", "M7"))
        problems = self._problems(text)
        self.assertTrue(any("P-001" in problem and "duplicate" in problem for problem in problems), problems)

    def test_the_summary_counts_rows_and_modules(self):
        rows = provenance.parse(LEDGER)
        ok, summary = provenance.summarise(rows)
        self.assertTrue(ok)
        self.assertIn(f"{len(rows)} rows", summary)
        self.assertIn(f"{len(provenance.MODULES)} modules covered", summary)


class CliTests(unittest.TestCase):
    def test_check_exits_zero_on_the_shipped_ledger(self):
        code, out = _call("--check")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("ok: "), out)
        self.assertIn("modules covered", out)

    def test_check_exits_non_zero_on_a_broken_ledger(self):
        with scratch_dir("prov") as tmp:
            path = _write(tmp, _three_origin_ledger(_row("P-020", "M7", "assisted", check="")))
            code, out = _call("--check", "--ledger", str(path))
        self.assertEqual(code, 1)
        self.assertIn("P-020", out)

    def test_a_missing_ledger_is_reported_not_crashed(self):
        missing = ROOT / ".scratch" / f"nope-{uuid.uuid4().hex[:8]}.md"
        code, out = _call("--check", "--ledger", str(missing))
        self.assertEqual(code, 2)
        self.assertIn("error:", out)

    def test_selftest_reports_the_ledger_shape(self):
        code, out = _call("--selftest")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("ok: "), out)


def _write_text(text: str) -> Path:
    """Write a ledger to a unique scratch file and hand back its path."""
    holder = scratch_dir("prov")
    tmp = holder.__enter__()
    _CLEANUP.append(holder)
    return _write(tmp, text)


_CLEANUP: list = []


def tearDownModule() -> None:
    for holder in _CLEANUP:
        holder.__exit__(None, None, None)
    _CLEANUP.clear()


if __name__ == "__main__":
    unittest.main()
