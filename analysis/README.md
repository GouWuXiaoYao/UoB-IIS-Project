# Analysis — from logs to a result table

One command, no network, no third-party packages:

```
python -m analysis.run --runs runs --run-id E-SIM-01 --out analysis
```

It reads only `runs/E-SIM-01/logs/**/*.jsonl` and writes:

| Output | What it is |
|---|---|
| `analysis/results.xlsx` | 7 sheets: README, Descriptives, Paired tests, Multiplicity, Checks, Figures, Sessions |
| `analysis/figures/fig1_outcome_bars.png` | mean debt change per condition, 95% CI whiskers |
| `analysis/figures/fig2_paired_slope.png` | per-task paired slope (baseline → governance) |
| `analysis/figures/fig3_events_per_session.png` | how many events the card adds (manipulation check) |
| `analysis/figures/fig4_distribution.png` | every session's task time, with the mean |
| `analysis/captions.md` | four paste-ready captions with n, test name and what the figure does **not** show |

`python -m analysis.run --selftest` checks the statistics, the workbook writer and the
PNG writer against known answers without touching `runs/`.

## Why these tests, and what they assume

All three are implemented and printed side by side. The point is not to pick whichever
looks significant; it is to show where they agree and where an assumption fails.

| Test | Used when | Assumption | What it is in this project |
|---|---|---|---|
| Paired t | default for a continuous outcome with one pair per task | differences approximately normal, no pair has a zero difference | The headline test. With 6 pairs the normal approximation is weak, which is why the Wilcoxon is printed next to it. |
| Wilcoxon signed-rank | n is small, or the differences are not plausibly normal | distribution of differences symmetric | Exact p by dynamic programming over subset sums when there are no ties; normal approximation with tie and continuity correction otherwise. With `n < 6` the exact p cannot go below 0.05, and the note says so. |
| Linear mixed model (random intercept) | repeated tasks per participant, unbalanced cells | random intercepts normal, residual variance constant | Implemented and validated (REML, profile over one variance ratio) but **not informative here**: one participant means the random intercept is collinear with the fixed intercept, so the function returns that reason instead of a fit. |

Effect sizes: `cohens_dz = mean(diff) / sd(diff)` and `hedges_g` (the small-sample
corrected form). Confidence intervals: Student t on the mean, plus a deterministic
bootstrap as a robustness check; when the variance is zero the interval is reported as
`undefined (no variance)` rather than as a zero-width interval.

## The three checks, each on its own sheet

- **Missing data** — expected cells vs actual log files, sessions without `session_end`,
  sessions without `task_end`, pairs missing one arm, and unreadable lines. Bad lines are
  counted and surfaced; they are never silently dropped.
- **Outliers** — median + MAD, flagged at `|z| > 3.5`. When MAD is zero the check declines
  to flag anything and says why: a 0/0 z-score would otherwise mark every observation.
- **Multiple comparisons** — Holm and Benjamini–Hochberg both printed, because under
  correlated metrics neither is exactly right. `gate_latency_ms` and `blocked_attempts`
  are excluded from the family and labelled `structural zero in baseline`: the baseline
  has no card and no gate, so its zero is a property of the condition, not a measurement.

## What this analysis does not show

The operator in these runs is a script (`govern/run.py::_rehearse`), and both
conditions receive the *same* replayed suggestion, so the outcome metrics are identical
by construction. Every zero-difference row means "nothing was manipulated", not "the
governance card does not help". A real claim needs human participants, which is
`planned` (see `docs/rubric-mapping.md` §6); the honest reading of the current run is
that the pipeline works end to end: 12 sessions in, one workbook and four figures out,
numbers identical to a hand recomputation of the logs.
