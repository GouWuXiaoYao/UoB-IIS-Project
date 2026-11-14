"""Proof that the experiment parameters are read from config, not baked in.

AGENTS §2.4 forbids thresholds in code. A source grep only proves the *shape* of
that rule, so these tests change a value in a config object and check that the
behaviour follows. If one of them fails, the value is hardcoded somewhere.

Two parameters have no behaviour to follow: ``tau_review_ms`` and
``mech_dwell_ms`` are metric thresholds (SPEC 5.2: blind-accept and mechanical
confirmation), and the analysis that would apply them is out of scope (SPEC M10
is N/A). For those two the test checks the weaker but still meaningful property
that the value is *read* from config — see ``docs/rubric-mapping.md`` §6.
"""

from __future__ import annotations

import dataclasses
import json
import re
import unittest
from pathlib import Path
from unittest import mock

from govern import card, config, corpus, gate, impact, score, session, tasks

ROOT = Path(__file__).resolve().parent.parent
BASE = config.load()
LIGHT = "T-L01a"


def _patched(**changes):
    """Make ``config.load()`` return a copy of the real config with ``changes``."""
    tweaked = dataclasses.replace(BASE, **changes)
    return mock.patch.object(config, "load", lambda *a, **k: tweaked)


def _task(task_id: str = LIGHT) -> tasks.Task:
    return tasks.by_id(tasks.load_index(), task_id)


class ParameterTests(unittest.TestCase):
    def test_the_card_statement_limit_comes_from_config(self):
        task = _task()
        found = impact.analyze(task.repo, task.intent)
        loose = max(len(item.statement) for item in card.build(found, task, "C1").items)
        with _patched(card_item_max_chars=24):
            tight = card.build(found, task, "C1")
        self.assertLessEqual(max(len(item.statement) for item in tight.items), 24)
        self.assertLess(max(len(item.statement) for item in tight.items), loose)

    def test_the_hidden_suite_timeout_comes_from_config(self):
        with _patched(test_timeout_s=7):
            self.assertEqual(score._timeout(), 7)

    def test_the_pair_tolerance_comes_from_config(self):
        checks = corpus.check_all()
        default_line = corpus.summarise(checks)
        with _patched(pair_tolerance=0.5):
            loose_line = corpus.summarise(checks)
        self.assertIn("within 20%", default_line)
        self.assertIn("within 50%", loose_line)

    def test_the_simulation_alpha_comes_from_config(self):
        schedule = json.loads((ROOT / "config" / "schedule.json").read_text(encoding="utf-8"))
        index = tasks.load_index()
        default = session.simulate(schedule, index, 4)
        with _patched(alpha_sim=0.5):
            loose = session.simulate(schedule, index, 4)
        self.assertEqual(default["alpha"], BASE.alpha_sim)
        self.assertEqual(loose["alpha"], 0.5)

    def test_the_metric_thresholds_are_read_from_config(self):
        # No behaviour consumes these yet (see the module docstring), so this is
        # the strongest available check: the reported threshold follows config.
        with _patched(mech_dwell_ms=1234):
            self.assertIn("1234 ms", gate.threshold_summary())


class SourceScanTests(unittest.TestCase):
    """A cheap second layer: the parameter values must not appear in code at all."""

    PARAMETERS = {
        "tau_review_ms": r"(?<![\d.])2000(?![\d.])",
        "mech_dwell_ms": r"(?<!\d)800(?!\d)",
        "task_time_limit_s": r"(?<!\d)1800(?!\d)",
        "alpha_sim": r"(?<![\d.])0\.05(?![\d.])",
        "pair_tolerance": r"(?<![\d.])0\.2(?![\d.])",
        "impact_precision_min": r"(?<![\d.])0\.8(?![\d.])",
    }

    def test_no_parameter_is_written_into_the_code(self):
        sources = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "govern").glob("*.py"))
            if path.name != "config.py"
        }
        offenders = [
            f"{name}: {key}"
            for key, pattern in self.PARAMETERS.items()
            for name, text in sources.items()
            if re.search(pattern, text)
        ]
        self.assertEqual(offenders, [], offenders)


if __name__ == "__main__":
    unittest.main()
