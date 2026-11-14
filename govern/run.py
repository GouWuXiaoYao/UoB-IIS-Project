"""Single CLI entry point: ``python -m govern.run``.

M0 exposes --selftest and --dry-run. The remaining flags are declared here so
that the interface is stable, and report "not implemented" until their
milestone lands (see docs/PLAN.md section 9).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, config, tasks

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_READY = 3


def _counts(config_path: str | Path = config.DEFAULT_PATH) -> tuple[int, int]:
    """Return (n_tasks, n_cards) over the corpus index."""
    config.load(config_path)  # fail fast on a broken config
    task_list = tasks.load_index()
    card_count = 0  # M4 will build one assessment card per task
    return len(task_list), card_count


def selftest(config_path: str | Path = config.DEFAULT_PATH) -> int:
    """Verify imports, config and the corpus index without touching anything."""
    n_tasks, n_cards = _counts(config_path)
    print(f"ok: {n_tasks} tasks, {n_cards} cards")
    return EXIT_OK


def dry_run(config_path: str | Path = config.DEFAULT_PATH) -> int:
    n_tasks, n_cards = _counts(config_path)
    print(f"ok: {n_tasks} tasks, {n_cards} cards")
    print("dry run: no logs written, no network used")
    return EXIT_OK


def _not_ready(flag: str) -> int:
    print(f"not implemented yet: {flag} (see docs/PLAN.md)", file=sys.stderr)
    return EXIT_NOT_READY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m govern.run",
        description="Interactive governance prototype for legacy refactoring.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--selftest", action="store_true", help="check config and corpus")
    parser.add_argument("--dry-run", action="store_true", help="validate wiring offline")
    parser.add_argument("--tasks", type=int, metavar="N", help="limit the number of tasks")

    session = parser.add_argument_group("single session")
    session.add_argument("--session", metavar="S-001")
    session.add_argument("--participant", metavar="P01")
    session.add_argument("--condition", choices=("C0", "C1"))
    session.add_argument("--task", metavar="T-L01a")
    session.add_argument("--port", type=int, metavar="8000")
    session.add_argument("--live", action="store_true", help="call the model API")

    batch = parser.add_argument_group("batch")
    batch.add_argument("--batch", action="store_true")
    batch.add_argument("--schedule", metavar="config/schedule.json")
    batch.add_argument("--run-id", metavar="R-001")
    batch.add_argument("--resume", metavar="runs/R-001/state/S-001.json")
    batch.add_argument("--simulate", type=int, metavar="N")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.dry_run:
        return dry_run()
    if args.session:
        return _not_ready("--session")
    if args.batch:
        return _not_ready("--batch")
    if args.resume:
        return _not_ready("--resume")
    if args.simulate is not None:
        return _not_ready("--simulate")

    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
