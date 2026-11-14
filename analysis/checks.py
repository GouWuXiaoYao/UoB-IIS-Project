"""The three checks the brief asks for, kept separate from the estimates.

1. **Missing data** — what the design expected versus what the logs contain, and
   why a pair was dropped from a test.
2. **Outliers** — robust z scores (median / MAD), because means and variances of
   small samples are exactly what a single wild value distorts.
3. **Multiplicity** — every test that shares a family gets Holm and
   Benjamini-Hochberg adjustments, so a table of six metrics is not read as six
   independent chances to be significant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .stats import benjamini_hochberg, holm


@dataclass
class MissingReport:
    expected_cells: int | None
    observed_sessions: int
    ended_sessions: int
    with_outcome: int
    without_outcome: list[str] = field(default_factory=list)
    unfinished: list[str] = field(default_factory=list)
    unpaired: list[str] = field(default_factory=list)
    duplicate_cells: list[str] = field(default_factory=list)
    bad_lines: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not (
            self.without_outcome
            or self.unfinished
            or self.unpaired
            or self.duplicate_cells
            or self.bad_lines
            or (self.expected_cells is not None and self.observed_sessions != self.expected_cells)
        )


def missing_report(
    sessions: Sequence[Any],
    manifests: Sequence[dict[str, Any]],
    baseline: str = "C0",
    treatment: str = "C1",
) -> MissingReport:
    expected = sum(int(m.get("n_cells") or 0) for m in manifests) or None
    report = MissingReport(
        expected_cells=expected,
        observed_sessions=len(sessions),
        ended_sessions=sum(1 for s in sessions if s.ended),
        with_outcome=sum(1 for s in sessions if s.tests_pass is not None),
    )
    cells: dict[tuple[str, str, str], list[str]] = {}
    for session in sessions:
        if session.n_bad_lines:
            report.bad_lines += session.n_bad_lines
        if not session.ended:
            report.unfinished.append(f"{session.session_id} (no session_end)")
        if session.tests_pass is None:
            report.without_outcome.append(f"{session.session_id} (no task_end)")
        cells.setdefault((session.participant, session.condition, session.task_id), []).append(
            session.session_id
        )
    for key, ids in sorted(cells.items()):
        if len(ids) > 1:
            report.duplicate_cells.append(f"{key[0]}/{key[1]}/{key[2]}: {len(ids)} sessions")

    keys: dict[tuple[str, str], set[str]] = {}
    for session in sessions:
        keys.setdefault(session.pair_key, set()).add(session.condition)
    for (participant, task), conditions in sorted(keys.items()):
        if {baseline, treatment} <= conditions:
            continue
        if conditions & {baseline, treatment}:
            missing = {baseline, treatment} - conditions
            report.unpaired.append(
                f"{participant}/{task}: no {', '.join(sorted(missing))} observation"
            )

    if expected is not None and len(sessions) != expected:
        report.notes.append(
            f"the run manifest expected {expected} cells but {len(sessions)} session logs "
            "were found; the difference is reported rather than filled in"
        )
    if not sessions:
        report.notes.append("no session logs matched the path given")
    return report


@dataclass
class OutlierReport:
    n: int
    median: float
    mad: float
    flagged: list[tuple[str, float, float]]
    method: str
    note: str = ""


def outliers(labels: Sequence[str], values: Sequence[float], threshold: float = 3.5) -> OutlierReport:
    """Robust z = 0.6745 * (x - median) / MAD; |z| > 3.5 is the usual flag.

    MAD is used because it has a 50% breakdown point: one wild session cannot
    move it, whereas one wild session can move a mean and its SD arbitrarily.
    """
    data = [float(v) for v in values]
    n = len(data)
    if n < 3:
        return OutlierReport(n, float("nan"), float("nan"), [], "not computed",
                             "fewer than three observations")
    ordered = sorted(data)
    mid = n // 2
    median = ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    deviations = sorted(abs(v - median) for v in data)
    mad = deviations[mid] if n % 2 else (deviations[mid - 1] + deviations[mid]) / 2
    if mad == 0:
        return OutlierReport(
            n, median, mad, [], "not computed",
            "MAD is zero: more than half the values are identical, so every "
            "deviation is infinitely many MADs away and the flag would be arbitrary",
        )
    flagged = []
    for label, value in zip(labels, data):
        z = 0.6745 * (value - median) / mad
        if abs(z) > threshold:
            flagged.append((label, value, z))
    return OutlierReport(
        n, median, mad, flagged,
        f"robust z = 0.6745*(x - median)/MAD, |z| > {threshold}",
        "" if not flagged else "flagged values are kept in the analysis and reported, not deleted",
    )


@dataclass
class MultiplicityReport:
    family: list[str]
    holm: list[dict[str, float | bool]]
    bh: list[dict[str, float | bool]]
    alpha: float
    note: str


def multiplicity(names: Sequence[str], p_values: Sequence[float], alpha: float = 0.05) -> MultiplicityReport:
    """Adjust a whole family of tests at once.

    Holm is the default report (family-wise control is what "did any of this
    hold?" asks); BH is shown next to it because with six correlated metrics the
    FWER correction is very conservative.
    """
    usable = [(n, p) for n, p in zip(names, p_values) if p is not None and not math.isnan(p)]
    if not usable:
        return MultiplicityReport(list(names), [], [], alpha, "no computable p-values")
    labels = [n for n, _ in usable]
    ps = [float(p) for _, p in usable]
    return MultiplicityReport(
        family=labels,
        holm=holm(ps, alpha),
        bh=benjamini_hochberg(ps, alpha),
        alpha=alpha,
        note=(
            f"{len(ps)} tests treated as one family; Holm controls the family-wise error "
            "rate, Benjamini-Hochberg controls the false discovery rate. With correlated "
            "metrics neither is exactly right, which is why both are printed."
        ),
    )


def family_rows(report: MultiplicityReport) -> Iterable[list[Any]]:
    for i, name in enumerate(report.family):
        h = report.holm[i]
        b = report.bh[i]
        yield [
            name,
            round(float(h["p"]), 4),
            round(float(h["p_adjusted"]), 4),
            "yes" if h["reject"] else "no",
            round(float(b["p_adjusted"]), 4),
            "yes" if b["reject"] else "no",
            report.alpha,
        ]
