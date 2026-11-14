"""Build the workbook, the figures and the captions from the loaded sessions.

The layout is deliberately boring: one sheet per question, every row traceable to
the session logs, and a caption file that can be pasted into the report. Figures
are drawn by :mod:`analysis.png` because matplotlib is not available; they are
plain, and the captions say what is drawn rather than what the author hopes it
shows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from . import checks, load, png, stats, xlsx

BASELINE = "C0"
TREATMENT = "C1"
CONDITION_LABEL = {"C0": "Baseline (C0)", "C1": "Governance (C1)"}

# metric key, human label, unit, primary?
METRICS: tuple[tuple[str, str, str], ...] = (
    ("debt_delta", "Debt change (weighted smells)", "smells"),
    ("vuln_delta", "Vulnerability change", "findings"),
    ("n_fail", "Failing hidden tests", "tests"),
    ("lines_added", "Lines added", "lines"),
    ("elapsed_ms", "Task time", "ms"),
    ("blocked_attempts", "Blocked generation attempts", "attempts"),
    ("gate_latency_ms", "Gate decision latency", "ms"),
    ("review_dwell_ms", "Review dwell before accept", "ms"),
)

# Metrics that exist in one arm only: the baseline has no card and therefore no
# gate. Comparing a measurement against a structural zero is not a test of an
# effect, so these are reported but kept out of the multiplicity family.
STRUCTURAL: dict[str, str] = {
    "blocked_attempts": "baseline has no card, so 0 is structural not measured",
    "gate_latency_ms": "baseline has no gate decision, so 0 is structural not measured",
}


def _fmt(value: Any, digits: int = 3) -> Any:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int,)):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf"
        return round(value, digits)
    return value


def _p(value: float | None) -> Any:
    if value is None:
        return "n/a"
    if math.isnan(value):
        return "n/a"
    if value < 0.001:
        return "<0.001"
    return round(value, 4)


@dataclass
class Figure:
    filename: str
    title: str
    caption: str
    path: Path | None = None


@dataclass
class Analysis:
    sessions: list[load.Session]
    manifests: list[dict[str, Any]]
    summaries: dict[str, dict[str, stats.Summary]] = field(default_factory=dict)
    tests: dict[str, stats.PairedResult] = field(default_factory=dict)
    missing: checks.MissingReport | None = None
    outlier_reports: dict[str, checks.OutlierReport] = field(default_factory=dict)
    multiplicity: checks.MultiplicityReport | None = None
    figures: list[Figure] = field(default_factory=list)


def _values(sessions: Sequence[load.Session], metric: str, condition: str) -> list[float]:
    out = []
    for session in sessions:
        if session.condition != condition:
            continue
        value = getattr(session, metric, None)
        if value is not None:
            out.append(float(value))
    return out


def analyse(sessions: list[load.Session], manifests: list[dict[str, Any]]) -> Analysis:
    analysis = Analysis(sessions=sessions, manifests=manifests)
    for metric, _label, _unit in METRICS:
        per_condition = {}
        for condition in (BASELINE, TREATMENT):
            values = _values(sessions, metric, condition)
            if values:
                per_condition[condition] = stats.summarise(values)
        if per_condition:
            analysis.summaries[metric] = per_condition

        labels, left, right, participants, _tasks = load.paired_series(
            sessions, metric, BASELINE, TREATMENT
        )
        if len(labels) >= 2:
            analysis.tests[metric] = stats.compare_paired(
                left, right, groups=participants
            )
        analysis.outlier_reports[metric] = checks.outliers(
            [
                f"{s.participant}/{s.condition}/{s.task_id}"
                for s in sessions
                if getattr(s, metric, None) is not None
            ],
            [
                float(getattr(s, metric))
                for s in sessions
                if getattr(s, metric, None) is not None
            ],
        )

    analysis.missing = checks.missing_report(sessions, manifests)
    names, p_values = [], []
    for metric, _label, _unit in METRICS:
        if metric in STRUCTURAL:
            continue
        result = analysis.tests.get(metric)
        if result is None or result.wilcoxon is None or result.wilcoxon.p_value is None:
            continue
        names.append(metric)
        p_values.append(float(result.wilcoxon.p_value))
    analysis.multiplicity = checks.multiplicity(names, p_values)
    return analysis


# --------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------
def _axes(canvas: png.Canvas, box: tuple[int, int, int, int], y_min: float, y_max: float,
          ticks: int = 5) -> tuple[int, int, int, int]:
    x, y, w, h = box
    canvas.fill_rect(x, y, 1, h, png.GREY)
    canvas.fill_rect(x, y + h, w, 1, png.GREY)
    for i in range(ticks + 1):
        value = y_min + (y_max - y_min) * i / ticks
        yy = y + h - round(h * i / ticks)
        canvas.fill_rect(x, yy, w, 1, png.LIGHT)
        canvas.text(x - 12 - canvas.text_width(f"{value:.2f}", 2), yy - 6, f"{value:.2f}", png.GREY, 2)
    return box


def _y_of(value: float, y_min: float, y_max: float, box: tuple[int, int, int, int]) -> int:
    _x, y, _w, h = box
    span = y_max - y_min or 1.0
    return y + h - round((value - y_min) / span * h)


def figure_bars(analysis: Analysis, metric: str, label: str, unit: str, target: Path) -> Figure:
    canvas = png.Canvas(900, 560)
    canvas.text(40, 26, f"MEAN {label.upper()} ({unit.upper()}) BY CONDITION", png.BLACK, 2)
    box = (120, 80, 720, 380)
    summaries = analysis.summaries.get(metric, {})
    lows, highs = [], []
    for summary in summaries.values():
        lows.append(summary.mean - (summary.ci_high - summary.mean if summary.ci_method == "t" else 0))
        highs.append(summary.mean + (summary.ci_high - summary.mean if summary.ci_method == "t" else 0))
    values = [s.mean for s in summaries.values()]
    y_min = min([0.0] + values + lows) if lows else min([0.0] + values)
    y_max = max([0.0] + values + highs) if highs else max([0.0] + values)
    pad = (y_max - y_min) * 0.18 or 1.0
    y_min, y_max = y_min - (pad if y_min < 0 else 0), y_max + pad
    _axes(canvas, box, y_min, y_max)

    order = [c for c in (BASELINE, TREATMENT) if c in summaries]
    slot = box[2] / (len(order) + 1)
    zero_y = _y_of(0.0, y_min, y_max, box)
    canvas.fill_rect(box[0], zero_y, box[2], 1, png.GREY)
    for i, condition in enumerate(order):
        summary = summaries[condition]
        cx = box[0] + slot * (i + 1)
        width = round(slot * 0.42)
        top = _y_of(summary.mean, y_min, y_max, box)
        colour = png.BLUE if condition == BASELINE else png.GREEN
        canvas.fill_rect(cx - width // 2, min(top, zero_y), width, abs(top - zero_y), colour)
        canvas.text_center(cx, min(top, zero_y) - 26, f"{summary.mean:.2f}", png.BLACK, 2)
        if summary.ci_method == "t":
            low = _y_of(summary.ci_low, y_min, y_max, box)
            high = _y_of(summary.ci_high, y_min, y_max, box)
            canvas.fill_rect(cx, high, 2, max(2, low - high), png.BLACK)
            canvas.fill_rect(cx - 9, high, 20, 2, png.BLACK)
            canvas.fill_rect(cx - 9, low - 2, 20, 2, png.BLACK)
        canvas.text_center(cx, box[1] + box[3] + 22, CONDITION_LABEL[condition].upper(), png.BLACK, 2)
        canvas.text_center(cx, box[1] + box[3] + 46, f"N={summary.n}", png.GREY, 1)
    canvas.text(40, 520, "WHISKERS: 95% CI OF THE MEAN (T).", png.GREY, 1)
    path = target / "fig1_outcome_bars.png"
    canvas.save(path)
    result = analysis.tests.get(metric)
    caption = (
        f"Figure 1. Mean {label.lower()} per condition, whiskers are 95% confidence intervals "
        f"of the mean (Student t). Sessions per condition: "
        + ", ".join(f"{c} n = {summaries[c].n}" for c in order)
        + ", paired by task."
    )
    if result is not None and result.zero_variance:
        caption += (
            " Every paired difference is exactly zero, so no interval for the difference exists; "
            "this is a property of the manipulation (the suggestion is identical in both arms), "
            "not evidence that the conditions are equivalent in general."
        )
    return Figure(path.name, "Mean by condition", caption, path)


def figure_slope(analysis: Analysis, metric: str, label: str, target: Path) -> Figure:
    canvas = png.Canvas(900, 560)
    canvas.text(40, 26, label.upper() + " PER TASK, PAIRED", png.BLACK, 2)
    box = (100, 80, 680, 380)
    _labels, left, right, _participants, tasks = load.paired_series(
        analysis.sessions, metric, BASELINE, TREATMENT
    )
    if not left:
        canvas.text(120, 240, "NO PAIRED OBSERVATIONS", png.GREY, 2)
        path = target / "fig2_paired_slope.png"
        canvas.save(path)
        return Figure(path.name, "Paired slope", "Figure 2. No paired observations were available.", path)
    low = min(left + right)
    high = max(left + right)
    pad = (high - low) * 0.2 or 1.0
    y_min, y_max = low - pad, high + pad
    _axes(canvas, box, y_min, y_max, 4)
    x0, x1 = box[0] + box[2] * 0.3, box[0] + box[2] * 0.7
    for i, (lv, rv, task) in enumerate(zip(left, right, tasks)):
        y0 = _y_of(lv, y_min, y_max, box)
        y1 = _y_of(rv, y_min, y_max, box)
        colour = png.GREY if lv != rv else png.LIGHT
        canvas.line(x0, y0, x1, y1, colour, 2)
        canvas.fill_rect(x0 - 3, y0 - 3, 7, 7, png.BLUE)
        canvas.fill_rect(x1 - 3, y1 - 3, 7, 7, png.GREEN)
        # Stagger labels: tasks in the same stratum have identical values, so their
        # lines coincide and un-staggered labels would print on top of each other.
        canvas.text(x1 + 12, y1 - 3 + (i % 3 - 1) * 9, task, png.GREY, 1)
    canvas.text_center(x0, box[1] + box[3] + 22, "BASELINE (C0)", png.BLUE, 2)
    canvas.text_center(x1, box[1] + box[3] + 22, "GOVERNANCE (C1)", png.GREEN, 2)
    canvas.text(40, 520, "EACH LINE JOINS THE SAME TASK IN THE TWO CONDITIONS.", png.GREY, 1)
    path = target / "fig2_paired_slope.png"
    canvas.save(path)
    n_flat = sum(1 for a, b in zip(left, right) if a == b)
    caption = (
        f"Figure 2. {label} for each task, paired by task (baseline left, governance right). "
        f"{n_flat} of {len(left)} pairs are exactly equal."
    )
    return Figure(path.name, "Paired slope", caption, path)


def figure_events(analysis: Analysis, target: Path) -> Figure:
    """What the manipulation actually changed: the length of the interaction.

    Blocked attempts are all zero for a scripted operator, so that chart would be
    three flat bars. The event count is the difference that does exist, and it is
    the honest way to show what the card adds to a session.
    """
    canvas = png.Canvas(900, 560)
    canvas.text(40, 26, "EVENTS PER SESSION (WHAT THE CARD ADDS)", png.BLACK, 2)
    box = (120, 80, 720, 360)
    means = {}
    counts = {}
    for condition in (BASELINE, TREATMENT):
        values = [float(s.n_events) for s in analysis.sessions if s.condition == condition]
        counts[condition] = len(values)
        means[condition] = sum(values) / len(values) if values else 0.0
    y_max = max(list(means.values()) + [1.0]) * 1.3
    _axes(canvas, box, 0.0, y_max, 4)
    slot = box[2] / 3
    for i, condition in enumerate((BASELINE, TREATMENT)):
        cx = box[0] + slot * (i + 1)
        top = _y_of(means.get(condition, 0.0), 0.0, y_max, box)
        colour = png.BLUE if condition == BASELINE else png.GREEN
        canvas.fill_rect(cx - 60, top, 120, box[1] + box[3] - top, colour)
        canvas.text_center(cx, top - 26, f"{means.get(condition, 0.0):.1f}", png.BLACK, 2)
        canvas.text_center(cx, box[1] + box[3] + 22, CONDITION_LABEL[condition].upper(), png.BLACK, 2)
        canvas.text_center(cx, box[1] + box[3] + 46, f"N={counts[condition]}", png.GREY, 1)
    canvas.text(40, 520, "ONE EVENT PER PROMPT, CARD ITEM, GATE DECISION, TEST RUN AND OUTCOME.",
                png.GREY, 1)
    path = target / "fig3_events_per_session.png"
    canvas.save(path)
    delta = means.get(TREATMENT, 0.0) - means.get(BASELINE, 0.0)
    caption = (
        f"Figure 3. Mean number of logged events per session: baseline "
        f"{means.get(BASELINE, 0.0):.1f}, governance {means.get(TREATMENT, 0.0):.1f} "
        f"(+{delta:.1f}, the card items and the gate decision). This is the manipulation, "
        "not an outcome: it measures how much interaction the card inserts, and says nothing "
        "about whether that interaction was read."
    )
    return Figure(path.name, "Events per session", caption, path)


def figure_dots(analysis: Analysis, metric: str, label: str, target: Path) -> Figure:
    canvas = png.Canvas(900, 480)
    canvas.text(40, 26, label.upper() + ": EVERY SESSION", png.BLACK, 2)
    box = (100, 80, 700, 300)
    values = {
        c: _values(analysis.sessions, metric, c) for c in (BASELINE, TREATMENT)
    }
    everything = [v for vs in values.values() for v in vs] or [0.0]
    y_min, y_max = min(everything), max(everything)
    pad = (y_max - y_min) * 0.25 or 1.0
    _axes(canvas, box, y_min - pad, y_max + pad, 4)
    for i, condition in enumerate((BASELINE, TREATMENT)):
        cx = box[0] + box[2] * (0.3 + 0.4 * i)
        colour = png.BLUE if condition == BASELINE else png.GREEN
        for j, value in enumerate(values[condition]):
            canvas.fill_rect(cx - 4 + (j % 3) * 4, _y_of(value, y_min - pad, y_max + pad, box) - 3, 7, 7, colour)
        if values[condition]:
            mean = sum(values[condition]) / len(values[condition])
            yy = _y_of(mean, y_min - pad, y_max + pad, box)
            canvas.fill_rect(cx - 30, yy, 62, 2, png.BLACK)
        canvas.text_center(cx, box[1] + box[3] + 22, CONDITION_LABEL[condition].upper(), png.BLACK, 2)
    canvas.text(40, 440, "BLACK BAR MARKS THE MEAN; POINTS ARE INDIVIDUAL SESSIONS.", png.GREY, 1)
    path = target / "fig4_distribution.png"
    canvas.save(path)
    caption = (
        f"Figure 4. Every session's {label.lower()}, by condition, with the mean marked. "
        "The spread is across tasks, not across participants: the operator is a script, so a "
        "wide spread here is task difficulty, not individual variation."
    )
    return Figure(path.name, "Distribution", caption, path)


# --------------------------------------------------------------------------
# workbook
# --------------------------------------------------------------------------
def _descriptive_rows(analysis: Analysis) -> Iterable[list[Any]]:
    yield ["Metric", "Condition", "n", "Mean", "SD", "Median", "Q1", "Q3", "Min", "Max",
           "95% CI low", "95% CI high", "CI method"]
    for metric, label, unit in METRICS:
        for condition, summary in analysis.summaries.get(metric, {}).items():
            yield [
                f"{label} [{unit}]", CONDITION_LABEL[condition], summary.n,
                _fmt(summary.mean), _fmt(summary.sd), _fmt(summary.median),
                _fmt(summary.q1), _fmt(summary.q3), _fmt(summary.minimum),
                _fmt(summary.maximum), _fmt(summary.ci_low), _fmt(summary.ci_high),
                summary.ci_method,
            ]


def _test_rows(analysis: Analysis) -> Iterable[list[Any]]:
    yield ["Metric", "Pairs", "Mean difference", "95% CI low", "95% CI high",
           "t", "df", "p (t)", "dz", "Hedges g", "W+", "p (Wilcoxon)", "rank-biserial",
           "LMM estimate", "LMM SE", "LMM p", "Status", "Note"]
    for metric, label, _unit in METRICS:
        result = analysis.tests.get(metric)
        if result is None:
            continue
        t = result.t
        w = result.wilcoxon
        lmm = result.lmm or {}
        note = " ".join(
            part for part in [(t.note if t else ""), (w.note if w else ""),
                              str(lmm.get("note", ""))] if part
        ).strip()
        status = "all differences zero" if result.zero_variance else "ok"
        if metric in STRUCTURAL:
            status = "structural zero in baseline"
            note = (note + " " + STRUCTURAL[metric]).strip()
        yield [
            label, result.n, _fmt(result.mean_difference),
            _fmt(t.ci_low if t else None), _fmt(t.ci_high if t else None),
            _fmt(t.statistic if t else None), _fmt(t.df if t else None), _p(t.p_value if t else None),
            _fmt(t.effect if t else None), _fmt(stats.hedges_g(result.differences)),
            _fmt(w.statistic if w else None), _p(w.p_value if w else None),
            _fmt(w.effect if w else None),
            _fmt(lmm.get("estimate")), _fmt(lmm.get("se")), _p(lmm.get("p_value")),
            status, note,
        ]


def _session_rows(analysis: Analysis) -> Iterable[list[Any]]:
    columns = list(analysis.sessions[0].as_row()) if analysis.sessions else []
    yield columns
    for session in analysis.sessions:
        row = session.as_row()
        yield [_fmt(row.get(c)) for c in columns]


def _check_rows(analysis: Analysis) -> Iterable[list[Any]]:
    missing = analysis.missing
    assert missing is not None
    yield ["Check", "Item", "Value"]
    yield ["missing", "expected cells (manifest)", _fmt(missing.expected_cells)]
    yield ["missing", "session logs found", missing.observed_sessions]
    yield ["missing", "sessions that ended", missing.ended_sessions]
    yield ["missing", "sessions with an outcome", missing.with_outcome]
    for label, items in (
        ("without outcome", missing.without_outcome),
        ("unfinished", missing.unfinished),
        ("unpaired", missing.unpaired),
        ("duplicate", missing.duplicate_cells),
        ("note", missing.notes),
    ):
        if not items:
            yield ["missing", label, "none"]
        for item in items:
            yield ["missing", label, item]
    yield ["missing", "verdict", "complete" if missing.complete else "reported above"]
    for metric, _label, _unit in METRICS:
        report = analysis.outlier_reports.get(metric)
        if report is None:
            continue
        yield ["outlier", metric, report.method]
        yield ["outlier", f"{metric} median", _fmt(report.median)]
        yield ["outlier", f"{metric} MAD", _fmt(report.mad)]
        if report.flagged:
            for label, value, z in report.flagged:
                yield ["outlier", f"{metric} flagged {label}", f"value={_fmt(value)} z={_fmt(z)}"]
        else:
            yield ["outlier", f"{metric} flagged", "none" if report.note == "" else report.note]


def _figure_rows(analysis: Analysis) -> Iterable[list[Any]]:
    yield ["File", "Title", "Caption"]
    for figure in analysis.figures:
        yield [figure.filename, figure.title, figure.caption]


def build_outputs(analysis: Analysis, out_dir: Path) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(exist_ok=True)

    if analysis.sessions:
        analysis.figures = [
            figure_bars(analysis, "debt_delta", "Debt change", "smells", figures_dir),
            figure_slope(analysis, "debt_delta", "Debt change", figures_dir),
            figure_events(analysis, figures_dir),
            figure_dots(analysis, "elapsed_ms", "Task time", figures_dir),
        ]

    provenance = [
        ["Analysis of the event logs", ""],
        ["generated by", "python -m analysis.run"],
        ["analysis package version", __import__("analysis").__version__],
        ["runs analysed", ", ".join(str(m.get("run_id")) for m in analysis.manifests) or "none"],
        ["session logs", len(analysis.sessions)],
        ["baseline condition", BASELINE],
        ["treatment condition", TREATMENT],
        ["data source", "runs/<run_id>/logs/**/*.jsonl only (AGENTS.md 2.6)"],
        ["", ""],
        ["What the tests are", ""],
        ["primary test", "Wilcoxon signed-rank (exact when untied), paired by task"],
        ["secondary", "paired t test; random-intercept mixed model as sensitivity analysis"],
        ["why Wilcoxon first", "n is small and the metrics are counts and milliseconds; the "
                               "signed-rank test does not assume normality and is robust to a "
                               "single extreme task, at the cost of power if the data are normal"],
        ["why t as well", "if the data are close to normal the t test is more powerful; both are "
                          "printed so a reader can see the conclusion does not depend on the choice"],
        ["why a mixed model", "it treats participant as a random effect; with a scripted operator "
                              "the participant variance is zero, so it should collapse to the "
                              "fixed effect. That collapse is itself a check on the design"],
        ["assumptions", "independence of tasks (defensible: separate checkouts); symmetry of "
                        "differences for Wilcoxon; approximate normality of differences for t; "
                        "normal random intercept and residual for the mixed model"],
        ["", ""],
        ["What this analysis cannot claim", ""],
        ["no people", "the operator is a script (SPEC Q1), so nothing here is a human-subjects result"],
        ["no equivalence", "a non-significant or uncomputable test is not evidence of no effect"],
        ["simulated suggestions", "the patches come from committed recordings marked source=sim"],
    ]
    for manifest in analysis.manifests:
        provenance.append(["", ""])
        provenance.append([f"run {manifest.get('run_id')}", ""])
        for key in ("app_version", "model_id", "model_temperature", "seed", "mode",
                    "conditions", "participants", "pairs", "repetitions", "n_cells",
                    "max_parallel", "task_order"):
            if key in manifest:
                provenance.append([f"  {key}", _fmt(manifest[key])])

    sheets: dict[str, list[list[Any]]] = {
        "README": provenance,
        "Descriptives": list(_descriptive_rows(analysis)),
        "Paired tests": list(_test_rows(analysis)),
        "Multiplicity": [["Metric", "p (raw)", "p Holm", "Holm reject", "p BH", "BH reject", "alpha"]]
        + [list(row) for row in checks.family_rows(analysis.multiplicity)]
        + [["", "", "", "", "", "", ""], ["note", analysis.multiplicity.note, "", "", "", "", ""]],
        "Checks": list(_check_rows(analysis)),
        "Figures": list(_figure_rows(analysis)),
        "Sessions": list(_session_rows(analysis)),
    }
    workbook = xlsx.write(out_dir / "results.xlsx", sheets)

    captions = ["# Figure captions", "",
                "Paste-ready captions. Everything below is computed from the logs under",
                "`runs/`; the numbers match `results.xlsx`.", ""]
    for figure in analysis.figures:
        captions.append(f"**{figure.filename}**")
        captions.append("")
        captions.append(figure.caption)
        captions.append("")
    caption_path = out_dir / "captions.md"
    caption_path.write_text("\n".join(captions), encoding="utf-8")

    return {"workbook": workbook, "captions": caption_path}
