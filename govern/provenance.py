"""Development provenance ledger and its checker (SPEC M11, PLAN milestone M10).

The A2 rubric asks for a development record that "distinguishes original, reused
and assisted work, with relevant examples of reviewing and adapting AI output".
A claim like that is worth nothing unless it is checkable, so the ledger
``docs/PROVENANCE.md`` is data and this module is the check:

* every module M1-M11 has at least one row,
* ``origin`` is not a single value repeated (all three appear at least once),
* every ``assisted`` row carries both a ``decision`` and a ``check`` -- the pair
  is the evidence that the output was reviewed rather than pasted,
* every ``reused`` row's ``source`` resolves to a real path in this workspace.

Exit codes: ``0`` ok, ``1`` the ledger is wrong, ``2`` the ledger is unreadable.

Usage::

    python -m govern.provenance --check
    python -m govern.provenance --check --ledger docs/PROVENANCE.md
    python -m govern.provenance --selftest
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "PROVENANCE.md"

MODULES = (
    "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11",
)
ORIGINS = ("original", "reused", "assisted")
FIELDS = ("item_id", "module", "origin", "source", "decision", "check", "commit")

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_UNREADABLE = 2


class LedgerError(ValueError):
    """The ledger cannot be read as a table at all."""


@dataclass(frozen=True)
class Row:
    item_id: str
    module: str
    origin: str
    source: str
    decision: str
    check: str
    commit: str
    line: int = 0

    @property
    def has_source(self) -> bool:
        return _filled(self.source)

    @property
    def has_decision(self) -> bool:
        return _filled(self.decision)

    @property
    def has_check(self) -> bool:
        return _filled(self.check)


def _filled(value: str) -> bool:
    """A dash is how a markdown table says "empty"; it must not count as content."""
    return bool(value) and value not in {"-", "—", "–"}


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(cells: Sequence[str]) -> bool:
    return all(set(cell) <= set("-: ") and cell for cell in cells)


def parse(path: str | Path = LEDGER) -> list[Row]:
    """Read the markdown table at ``path`` into rows.

    Prose before the table is allowed and ignored; a table row with the wrong
    number of cells is an error, because silently dropping a column is exactly
    how an "assisted" row loses its evidence.
    """
    text = Path(path).read_text(encoding="utf-8")
    rows: list[Row] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _cells(stripped)
        if _is_separator(cells):
            continue
        if cells and cells[0].lower() == "item_id":
            continue
        if len(cells) != len(FIELDS):
            raise LedgerError(
                f"{path}: line {number}: expected {len(FIELDS)} cells, found {len(cells)}"
            )
        rows.append(Row(*cells, line=number))
    if not rows:
        raise LedgerError(f"{path}: no ledger rows found")
    return rows


def _source_exists(source: str, root: Path) -> bool:
    candidate = source.split("`")[0].strip()
    if not candidate:
        return False
    return (root / candidate).exists()


def check(rows: Iterable[Row], root: Path = ROOT) -> list[str]:
    """Return every problem with ``rows``; an empty list means the ledger is ok."""
    rows = list(rows)
    problems: list[str] = []

    covered = {row.module for row in rows}
    missing = [module for module in MODULES if module not in covered]
    if missing:
        problems.append(f"modules with no provenance row: {', '.join(missing)}")

    seen: set[str] = set()
    duplicated: set[str] = set()
    for row in rows:
        if row.item_id in seen:
            duplicated.add(row.item_id)
        seen.add(row.item_id)
    for item_id in sorted(duplicated):
        problems.append(f"{item_id}: duplicate item_id")

    origins = {row.origin for row in rows}
    for origin in ORIGINS:
        if origin not in origins:
            problems.append(
                f"origin '{origin}' never appears: a ledger that does not distinguish "
                "original, reused and assisted work cannot be checked"
            )

    for row in rows:
        if row.origin not in ORIGINS:
            problems.append(f"{row.item_id}: origin '{row.origin}' is not one of {', '.join(ORIGINS)}")
        if row.module not in MODULES:
            problems.append(f"{row.item_id}: module '{row.module}' is not one of M1-M11")
        if row.origin == "assisted":
            if not row.has_decision:
                problems.append(f"{row.item_id}: assisted work needs a decision (why this was kept)")
            if not row.has_check:
                problems.append(f"{row.item_id}: assisted work needs a check (how it was verified)")
        if row.origin == "reused":
            if not row.has_source:
                problems.append(f"{row.item_id}: reused work needs a source")
            elif not _source_exists(row.source, root):
                problems.append(f"{row.item_id}: reused source '{row.source}' does not exist in the workspace")
    return problems


def summarise(rows: Sequence[Row]) -> tuple[bool, str]:
    """Return ``(ok, line)`` for the terminal."""
    covered = sorted({row.module for row in rows})
    counts = {origin: sum(1 for row in rows if row.origin == origin) for origin in ORIGINS}
    line = (
        f"{len(rows)} rows, {len(covered)} modules covered "
        f"(original={counts['original']}, reused={counts['reused']}, assisted={counts['assisted']})"
    )
    return True, line


def report(rows: Sequence[Row], problems: Sequence[str]) -> str:
    if problems:
        head = f"fail: {len(problems)} problem(s) in the provenance ledger"
        return "\n".join([head, *[f"  - {problem}" for problem in problems]])
    _, line = summarise(rows)
    return f"ok: {line}"


def _selftest() -> int:
    sample = [
        Row("P-001", "M1", "original", "", "d", "c", "abc123"),
        Row("P-002", "M2", "reused", "govern", "d", "c", "abc123"),
        Row("P-003", "M3", "assisted", "", "d", "c", "abc123"),
    ]
    problems = check([*sample, *[Row(f"P-1{n:02d}", module, "original", "", "d", "c", "abc123") for n, module in enumerate(MODULES[3:], start=4)]])
    if problems:
        print("fail: the self-test fixture itself is wrong", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return EXIT_FAIL
    broken = [row for row in sample if row.origin != "assisted"] + [
        Row("P-009", "M9", "assisted", "", "d", "", "abc123")
    ]
    still_fine = check([*broken, *[Row(f"Q-1{n:02d}", module, "original", "", "d", "c", "abc123") for n, module in enumerate(MODULES[4:], start=5)]])
    if not any("P-009" in problem for problem in still_fine):
        print("fail: an assisted row without a check was accepted", file=sys.stderr)
        return EXIT_FAIL
    print(f"ok: {len(MODULES)} modules, {len(ORIGINS)} origins, assisted rows must carry decision + check")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m govern.provenance")
    parser.add_argument("--check", action="store_true", help="validate the ledger")
    parser.add_argument("--ledger", default=str(LEDGER), help="path to PROVENANCE.md")
    parser.add_argument("--selftest", action="store_true", help="check the checker")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.check:
        parser.print_help()
        return EXIT_OK

    try:
        rows = parse(args.ledger)
    except (OSError, LedgerError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNREADABLE

    problems = check(rows)
    print(report(rows, problems), file=sys.stderr if problems else sys.stdout)
    return EXIT_FAIL if problems else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
