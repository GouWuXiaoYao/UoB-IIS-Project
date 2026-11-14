"""CLI: ``python -m experiments.run --config conditions.yaml [--dry-run]``.

Exit codes: ``0`` every scheduled session finished, ``1`` the batch ran but at
least one cell failed (see ``runs/<run_id>/failures.jsonl``), ``2`` the file or
the arguments are unusable — nothing was started.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from experiments import runner
from experiments import spec as spec_mod

DEFAULT_CONFIG = Path("conditions.yaml")
EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_USAGE = 2


def _usage(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def table(data: dict[str, Any]) -> str:
    """The result table a reader can paste into a report."""
    rows = ["| condition | sessions | escape rate | mean debt Δ | OTI | mechanical |",
            "|---|---|---|---|---|---|"]
    for name, block in data["conditions"].items():
        rows.append(
            "| {name} | {n} | {escape} | {debt} | {oti} | {mech} |".format(
                name=name,
                n=_fmt(block["n_sessions"]),
                escape=_fmt(block["escape_defect_rate"]),
                debt=_fmt(block["mean_debt_delta"]),
                oti=_fmt(block["oti"]),
                mech=_fmt(block["mechanical_share"]),
            )
        )
    return "\n".join(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m experiments.run")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="experiment file (YAML subset or JSON)")
    parser.add_argument("--run-id", help="override the run_id from the file")
    parser.add_argument("--runs-root", default=str(runner.RUNS_ROOT), help="where runs/<run_id>/ lives")
    parser.add_argument("--workers", type=int, help="override concurrency.max_parallel")
    parser.add_argument("--resume", action="store_true", help="skip cells whose log already ended")
    parser.add_argument("--limit", type=int, help="run at most N cells (debugging)")
    parser.add_argument("--dry-run", action="store_true", help="validate and print the plan; write nothing")
    parser.add_argument("--json", dest="as_json", action="store_true", help="print metrics.json to stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        loaded = spec_mod.load(args.config)
    except spec_mod.SpecError as exc:
        return _usage(f"cannot use {args.config}: {exc}")

    if args.run_id:
        try:
            loaded = spec_mod.validate({**loaded.raw, "run_id": args.run_id})
        except spec_mod.SpecError as exc:
            return _usage(str(exc))

    if args.workers is not None and args.workers < 1:
        return _usage("--workers must be at least 1")

    try:
        task_list = spec_mod.load_tasks(loaded)
    except spec_mod.SpecError as exc:
        return _usage(str(exc))

    planned = runner.plan(loaded, task_list)

    if args.dry_run:
        print(
            f"ok: {len(planned['conditions'])} conditions × {len(task_list)} tasks × "
            f"{len(planned['participants'])} participant(s) × {planned['repetitions']} repetition(s) "
            f"= {planned['n_cells']} sessions (concurrency {planned['max_parallel']})"
        )
        pairs = ", ".join(f"{name}={code}" for name, code in sorted(planned["conditions"].items()))
        print(f"plan: {pairs}; tasks {', '.join(planned['task_order'])}")
        print("dry run: no logs written, no network used")
        return EXIT_OK

    report = runner.execute(
        loaded,
        runs_root=args.runs_root,
        workers=args.workers,
        resume=args.resume,
        limit=args.limit,
    )

    if args.as_json:
        print(json.dumps(report["metrics"], indent=2, ensure_ascii=False))
    else:
        print(table(report["metrics"]))
        print(
            f"\nok: {report['n_ran']} ran, {report['n_skipped']} skipped, {report['n_failed']} failed "
            f"of {report['n_total']} → {report['run_dir']}"
        )
    if report["n_failed"]:
        print(f"note: failures recorded in {Path(report['run_dir']) / 'failures.jsonl'}", file=sys.stderr)
        return EXIT_PARTIAL
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
