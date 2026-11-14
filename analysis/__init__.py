"""Analysis of the JSONL logs produced by ``govern`` (SPEC M10 / Q8 planned layer).

The layer is deliberately standard library only, like the rest of the repository
(AGENTS.md section 1). That means writing the .xlsx and the .png files by hand
instead of pulling in openpyxl and matplotlib:

* ``analysis/xlsx.py``  — a minimal SpreadsheetML writer (zip of XML parts).
* ``analysis/png.py``   — a minimal raster canvas (zlib + a 5x7 bitmap font).
* ``analysis/stats.py`` — descriptives, effect sizes, bootstrap and analytic
  confidence intervals, paired t, exact Wilcoxon signed-rank, a random-intercept
  linear mixed model, and the multiplicity corrections.
* ``analysis/load.py``  — logs -> one record per session.
* ``analysis/checks.py``— missing data, outliers, the multiplicity family.
* ``analysis/report.py``— workbook, figures, captions.
* ``analysis/run.py``   — ``python -m analysis.run --runs runs --out analysis/out``.

Every number in the output is computed from the JSONL files; nothing is typed in.
"""

__all__ = ["checks", "load", "png", "report", "stats", "xlsx"]

__version__ = "1.0.0"
