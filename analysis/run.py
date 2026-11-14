"""``python -m analysis.run`` — logs in, workbook and figures out.

    python -m analysis.run --runs runs --out analysis/out

The command prints the same numbers it writes, so a reader can check the workbook
against the terminal. ``--selftest`` runs the known-answer checks that the test
suite also runs (a module convention from AGENTS.md section 3).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path

from . import checks, load, png, report, stats, xlsx

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS = ROOT / "runs"


@contextmanager
def _scratch():
    """A writable throw-away directory inside the repository.

    ``tempfile`` is not usable under the project's sandbox (the directory it
    hands back cannot be written to), which is the same reason ``tests/_scratch.py``
    exists. Keeping the scratch area inside the repository also keeps it on the
    same filesystem rules as everything else.
    """
    path = ROOT / ".scratch" / f"analysis-selftest-{os.getpid()}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _build(args: argparse.Namespace) -> tuple[report.Analysis, dict[str, Path]]:
    root = Path(args.runs)
    candidates = load.discover(root)
    if args.run_id:
        candidates = [p for p in candidates if p.name == args.run_id]
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        raise SystemExit(
            f"fail: {root} holds more than one run ({names}); pick one with --run-id. "
            "Pooling them would count the same cells twice."
        )
    if not candidates:
        raise SystemExit(f"fail: no session logs under {root}")
    run_dir = candidates[0]
    sessions = load.load_run(run_dir)
    manifest = load.read_manifest(run_dir)
    manifest["_sessions"] = len(sessions)
    if args.baseline != report.BASELINE or args.treatment != report.TREATMENT:
        report.BASELINE, report.TREATMENT = args.baseline, args.treatment
    analysis = report.analyse(sessions, [manifest])
    outputs = report.build_outputs(analysis, Path(args.out))
    return analysis, outputs


def _table(analysis: report.Analysis) -> list[str]:
    lines = [
        f"{'metric':<34}{'n':>4}{'mean C0':>10}{'mean C1':>10}{'diff':>9}{'p Wilcoxon':>12}{'note':>6}",
    ]
    for metric, label, _unit in report.METRICS:
        result = analysis.tests.get(metric)
        if result is None:
            continue
        means = analysis.summaries.get(metric, {})
        left = f"{means[report.BASELINE].mean:.2f}" if report.BASELINE in means else "-"
        right = f"{means[report.TREATMENT].mean:.2f}" if report.TREATMENT in means else "-"
        p = result.wilcoxon.p_value if result.wilcoxon else None
        p_text = "n/a" if p is None else ("<0.001" if p < 0.001 else f"{p:.3f}")
        flag = "zero" if result.zero_variance else ("struct" if metric in report.STRUCTURAL else "")
        lines.append(
            f"{label[:33]:<34}{result.n:>4}{left:>10}{right:>10}"
            f"{result.mean_difference:>9.2f}{p_text:>12}{flag:>6}"
        )
    missing = analysis.missing
    if missing is not None:
        lines.append("")
        lines.append(
            f"missing: expected {missing.expected_cells or 'unknown'}, found "
            f"{missing.observed_sessions} sessions, {missing.ended_sessions} ended, "
            f"{missing.with_outcome} with an outcome"
        )
        for label, items in (
            ("without outcome", missing.without_outcome),
            ("unfinished", missing.unfinished),
            ("unpaired", missing.unpaired),
            ("duplicate", missing.duplicate_cells),
        ):
            if items:
                lines.append(f"  {label}: {len(items)} ({items[0]} ...)")
        if missing.notes:
            for note in missing.notes:
                lines.append(f"  note: {note}")
    multiplicity = analysis.multiplicity
    if multiplicity and multiplicity.family:
        rejected = sum(1 for row in multiplicity.holm if row["reject"])
        lines.append(
            f"multiplicity: {len(multiplicity.family)} tests, {rejected} survive Holm at "
            f"alpha={multiplicity.alpha}"
        )
    return lines


def _selftest() -> int:
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        if not condition:
            failures.append(f"{name} {detail}".strip())

    # Known answers: differences 1..6 (mean 3.5, sd 1.8708) give t = 4.5826, df = 5,
    # a two-sided p of 0.005934, dz = 1.8708, and an exact Wilcoxon p of 0.03125.
    before = [10, 12, 14, 16, 18, 20]
    after = [9, 10, 11, 12, 13, 14]
    result = stats.compare_paired(before, after)
    check("paired t", abs((result.t.statistic or 0) - 4.5826) < 1e-3, f"got {result.t.statistic}")
    check("paired t p", abs((result.t.p_value or 0) - 0.005934) < 5e-5, f"got {result.t.p_value}")
    check("wilcoxon", (result.wilcoxon.p_value or 0) == 0.03125, f"got {result.wilcoxon.p_value}")
    check("dz", abs((result.t.effect or 0) - 1.8708) < 1e-3, f"got {result.t.effect}")
    check("t cdf 2.0 df 10", abs(stats.t_cdf(2.0, 10) - 0.9633) < 1e-3, f"got {stats.t_cdf(2.0, 10)}")
    zero = stats.compare_paired([1, 2, 3], [1, 2, 3])
    check("zero variance", zero.zero_variance and zero.t.p_value is None)

    with _scratch() as tmp:
        book = xlsx.write(tmp / "t.xlsx", {"A": [["x", "y"], ["a", 1.5]]})
        back = xlsx.read_sheets(book)
        check("xlsx round trip", back.get("A") == [["x", "y"], ["a", "1.5"]], f"got {back}")
        canvas = png.Canvas(40, 30)
        canvas.text(2, 2, "OK", png.BLACK, 1)
        png_path = canvas.save(tmp / "t.png")
        check("png signature", png_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("ok: statistics, workbook and png writer reproduce their known answers")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m analysis.run", description=__doc__)
    parser.add_argument("--runs", default=str(DEFAULT_RUNS), help="run directory or a directory of runs")
    parser.add_argument("--run-id", default=None, help="which run to analyse when --runs holds several")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--baseline", default=report.BASELINE)
    parser.add_argument("--treatment", default=report.TREATMENT)
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not Path(args.runs).exists():
        print(f"fail: no such path: {args.runs}", file=sys.stderr)
        return 2

    analysis, outputs = _build(args)
    if not analysis.sessions:
        print(f"fail: no session logs under {args.runs}", file=sys.stderr)
        return 2

    if args.json:
        payload = {
            "sessions": len(analysis.sessions),
            "runs": [m.get("run_id") for m in analysis.manifests],
            "tests": {
                metric: {
                    "n": result.n,
                    "mean_difference": result.mean_difference,
                    "wilcoxon_p": (result.wilcoxon.p_value if result.wilcoxon else None),
                    "t_p": (result.t.p_value if result.t else None),
                    "zero_variance": result.zero_variance,
                }
                for metric, result in analysis.tests.items()
            },
            "outputs": {name: str(path) for name, path in outputs.items()},
        }
        print(json.dumps(payload, indent=2))
    else:
        for line in _table(analysis):
            print(line)
        print()
        print(f"ok: {len(analysis.sessions)} session logs, {len(analysis.figures)} figures")
        for name, path in outputs.items():
            print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
