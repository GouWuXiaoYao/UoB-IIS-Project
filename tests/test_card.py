"""Acceptance tests for the assessment card (SPEC M5, PLAN milestone M4)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from govern import card as card_mod
from govern import config, impact, tasks

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
CONFIG = config.load(ROOT / "config" / "config.json")
CONDITION = "C1"


def _task(task_id: str = "T-L01a") -> tasks.Task:
    return tasks.by_id(tasks.load_index(CORPUS), task_id)


def _cards():
    for task in tasks.load_index(CORPUS):
        result = impact.analyze(task.repo, task.intent)
        yield task, result, card_mod.build(result, task, CONDITION)


class CardShapeTests(unittest.TestCase):
    def test_every_card_has_at_least_three_items(self) -> None:
        for task, _result, card in _cards():
            with self.subTest(task=task.task_id):
                self.assertGreaterEqual(card.n_items, 3)

    def test_statements_are_short_and_name_a_symbol(self) -> None:
        for task, _result, card in _cards():
            for item in card.items:
                with self.subTest(task=task.task_id, item=item.item_id):
                    self.assertLessEqual(len(item.statement), CONFIG.card_item_max_chars)
                    self.assertIn(item.affected_symbol, item.statement)

    def test_no_item_without_a_source_in_the_impact_set(self) -> None:
        for task, result, card in _cards():
            symbols = {entry.symbol for entry in result.items}
            with self.subTest(task=task.task_id):
                for item in card.items:
                    self.assertIn(item.affected_symbol, symbols)

    def test_evidence_points_at_a_real_impact_item(self) -> None:
        for task, result, card in _cards():
            ids = {entry.item_id for entry in result.items}
            with self.subTest(task=task.task_id):
                for item in card.items:
                    self.assertIn(item.evidence_ref, ids)

    def test_c1_puts_the_whole_impact_set_on_the_card(self) -> None:
        for task, result, card in _cards():
            with self.subTest(task=task.task_id):
                self.assertEqual(card.n_items, len(result.items))
                self.assertEqual(card.n_required, card.n_items)
                self.assertEqual(set(card.required_ids), {i.item_id for i in card.items})

    def test_item_ids_are_unique(self) -> None:
        for _task_, _result, card in _cards():
            ids = [item.item_id for item in card.items]
            self.assertEqual(len(ids), len(set(ids)))


class CardDeterminismTests(unittest.TestCase):
    def test_building_twice_gives_the_same_card(self) -> None:
        task = _task()
        result = impact.analyze(task.repo, task.intent)
        first = card_mod.build(result, task, CONDITION)
        second = card_mod.build(result, task, CONDITION)
        self.assertEqual(first, second)

    def test_rendering_twice_gives_the_same_html(self) -> None:
        task = _task()
        result = impact.analyze(task.repo, task.intent)
        card = card_mod.build(result, task, CONDITION)
        self.assertEqual(card_mod.to_html(card), card_mod.to_html(card))

    def test_cards_differ_between_tasks(self) -> None:
        ids = set()
        for _task_, _result, card in _cards():
            ids.add(card.card_id)
        self.assertEqual(len(ids), 6)


class NoDiffBeforeConfirmationTests(unittest.TestCase):
    """SPEC M5 acceptance 4: the card must not leak the answer."""

    def test_html_does_not_contain_any_added_line_from_the_gold_patch(self) -> None:
        task = _task("T-L03a")
        added = [
            line[1:].strip()
            for line in task.gold_patch.read_text(encoding="utf-8").splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        added = [line for line in added if len(line) > 8]
        self.assertTrue(added, "the gold patch should have substantive added lines")

        result = impact.analyze(task.repo, task.intent)
        html = card_mod.to_html(card_mod.build(result, task, CONDITION))
        for line in added:
            with self.subTest(line=line[:40]):
                self.assertNotIn(line, html)

    def test_html_never_renders_a_pre_ticked_checkbox(self) -> None:
        """A pre-ticked box is mechanical confirmation by construction."""
        for task, _result, card in (c for c in _cards() if c[2].items):
            html = card_mod.to_html(card)
            with self.subTest(task=task.task_id):
                self.assertNotIn(" checked", html)

    def test_required_items_are_marked_but_not_confirmed(self) -> None:
        task = _task()
        card = card_mod.build(impact.analyze(task.repo, task.intent), task, CONDITION)
        html = card_mod.to_html(card)
        self.assertEqual(html.count('data-required="true"'), card.n_required)
        self.assertEqual(html.count('class="required"'), card.n_required)

    def test_html_has_no_code_block_or_patch_hunk(self) -> None:
        task = _task("T-L03a")
        result = impact.analyze(task.repo, task.intent)
        html = card_mod.to_html(card_mod.build(result, task, CONDITION))
        self.assertNotIn("@@", html)
        self.assertNotIn("<pre", html)
        self.assertIsNone(re.search(r"(?m)^\+", html))


class ConditionTests(unittest.TestCase):
    def test_unknown_condition_is_rejected(self) -> None:
        task = _task()
        result = impact.analyze(task.repo, task.intent)
        with self.assertRaises(ValueError):
            card_mod.build(result, task, "C9")

    def test_c0_baseline_card_requires_nothing(self) -> None:
        task = _task()
        result = impact.analyze(task.repo, task.intent)
        baseline = card_mod.build(result, task, "C0")
        self.assertEqual(baseline.n_items, 0)
        self.assertEqual(baseline.n_required, 0)
        self.assertEqual(baseline.required_ids, ())

    def test_c0_and_c1_cards_are_distinct(self) -> None:
        task = _task()
        result = impact.analyze(task.repo, task.intent)
        self.assertNotEqual(
            card_mod.build(result, task, "C0").card_id,
            card_mod.build(result, task, "C1").card_id,
        )


if __name__ == "__main__":
    unittest.main()
