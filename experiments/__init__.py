"""Experiment orchestration: conditions, cells, runs, metrics.

`govern/` is the instrument (one session at a time); this package is the bench
that runs the instrument many times and records what happened. Nothing here
talks to a model directly — every session goes through `govern.session`.
"""

from __future__ import annotations

__all__ = ["spec", "runner", "metrics"]
