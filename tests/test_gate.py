"""Acceptance tests for the mandatory confirmation gate (SPEC M6, PLAN M4)."""

from __future__ import annotations

import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path

from govern import card as card_mod
from govern import config, gate as gate_mod, impact, tasks

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
CONDITION = "C1"


class FakeClock:
    """Deterministic clock: each call advances by the given number of seconds."""

    def __init__(self, step: float = 0.0) -> None:
        self.now = 1000.0
        self.step = step

    def __call__(self) -> float:
        current = self.now
        self.now += self.step
        return current


def _card(task_id: str = "T-L01a") -> card_mod.Card:
    task = tasks.by_id(tasks.load_index(CORPUS), task_id)
    result = impact.analyze(task.repo, task.intent)
    return card_mod.build(result, task, CONDITION)


class BlockingTests(unittest.TestCase):
    def test_a_fresh_gate_blocks(self) -> None:
        decision = gate_mod.Gate(_card()).decide()
        self.assertTrue(decision.blocked)
        self.assertFalse(decision.confirmed)
        self.assertEqual(decision.n_confirmed, 0)
        self.assertGreater(decision.n_required, 0)

    def test_partial_confirmation_still_blocks(self) -> None:
        card = _card()
        gate = gate_mod.Gate(card)
        for item_id in card.required_ids[:-1]:
            gate.toggle(item_id)
        decision = gate.decide()
        self.assertTrue(decision.blocked)
        self.assertEqual(decision.n_confirmed, card.n_required - 1)

    def test_full_confirmation_unlocks(self) -> None:
        card = _card()
        gate = gate_mod.Gate(card)
        for item_id in card.required_ids:
            gate.toggle(item_id)
        decision = gate.decide()
        self.assertFalse(decision.blocked)
        self.assertTrue(decision.confirmed)
        self.assertEqual(decision.n_confirmed, card.n_required)
        self.assertTrue(gate.open())

    def test_unticking_locks_again(self) -> None:
        card = _card()
        gate = gate_mod.Gate(card)
        for item_id in card.required_ids:
            gate.toggle(item_id)
        self.assertTrue(gate.open())
        gate.toggle(card.required_ids[0])
        self.assertFalse(gate.open())
        self.assertTrue(gate.decide().blocked)


class ToggleTests(unittest.TestCase):
    def test_toggle_reports_checked_state_and_dwell(self) -> None:
        gate = gate_mod.Gate(_card(), clock=FakeClock(step=0.5))
        item_id = _card().items[0].item_id
        checked, dwell_ms = gate.toggle(item_id)
        self.assertTrue(checked)
        self.assertIsInstance(dwell_ms, int)
        self.assertGreaterEqual(dwell_ms, 0)
        checked, _dwell = gate.toggle(item_id)
        self.assertFalse(checked)

    def test_unknown_item_is_rejected(self) -> None:
        gate = gate_mod.Gate(_card())
        with self.assertRaises(KeyError):
            gate.toggle("no-such-item")

    def test_dwell_reflects_the_clock(self) -> None:
        gate = gate_mod.Gate(_card(), clock=FakeClock(step=1.5))
        first = gate.toggle(_card().items[0].item_id)
        second = gate.toggle(_card().items[1].item_id)
        self.assertEqual(first[1], 1500)
        self.assertEqual(second[1], 1500)


class TokenTests(unittest.TestCase):
    def test_no_token_while_blocked(self) -> None:
        gate = gate_mod.Gate(_card())
        self.assertIsNone(gate.issue_token())
        self.assertFalse(gate.consume_token())

    def test_token_is_single_use(self) -> None:
        card = _card()
        gate = gate_mod.Gate(card)
        for item_id in card.required_ids:
            gate.toggle(item_id)
        token = gate.issue_token()
        self.assertIsInstance(token, str)
        self.assertTrue(gate.consume_token())
        self.assertFalse(gate.consume_token(), "the token must not be reusable")

    def test_changing_an_answer_invalidates_the_live_token(self) -> None:
        card = _card()
        gate = gate_mod.Gate(card)
        for item_id in card.required_ids:
            gate.toggle(item_id)
        self.assertIsNotNone(gate.issue_token())
        gate.toggle(card.required_ids[0])
        gate.toggle(card.required_ids[0])
        self.assertFalse(gate.consume_token(), "a re-confirmed token must be re-issued")


class BypassTests(unittest.TestCase):
    """SPEC M6 acceptance 3: no public way around the gate."""

    def test_a_new_gate_does_not_inherit_confirmations(self) -> None:
        card = _card()
        first = gate_mod.Gate(card)
        for item_id in card.required_ids:
            first.toggle(item_id)
        second = gate_mod.Gate(card)
        self.assertTrue(second.decide().blocked)
        self.assertFalse(second.consume_token())

    def test_a_card_that_understates_what_is_required_is_rejected(self) -> None:
        card = _card()
        forged = replace(card, required_ids=card.required_ids[:-1])
        with self.assertRaises(ValueError):
            gate_mod.Gate(forged)

    def test_a_card_that_inflates_the_required_count_is_rejected(self) -> None:
        card = _card()
        forged = replace(card, n_required=card.n_required + 1)
        with self.assertRaises(ValueError):
            gate_mod.Gate(forged)

    def test_a_required_id_that_is_not_on_the_card_is_rejected(self) -> None:
        card = _card()
        forged = replace(card, required_ids=card.required_ids + ("ghost-item",), n_required=card.n_required + 1)
        with self.assertRaises(ValueError):
            gate_mod.Gate(forged)

    def test_there_is_no_attribute_that_unlocks_the_gate(self) -> None:
        gate = gate_mod.Gate(_card())
        for name in ("checked", "confirmed", "unlock", "force", "skip", "bypass"):
            self.assertFalse(hasattr(gate, name), f"{name} would be a bypass")
        self.assertTrue(gate.decide().blocked)


class PassThroughTests(unittest.TestCase):
    """SPEC M6 acceptance 4: C0 uses the same interface and never blocks."""

    def test_passthrough_never_blocks(self) -> None:
        gate = gate_mod.PassThroughGate(_card())
        decision = gate.decide()
        self.assertFalse(decision.blocked)
        self.assertTrue(decision.confirmed)
        self.assertTrue(gate.open())

    def test_passthrough_still_reports_the_card_shape(self) -> None:
        card = _card()
        decision = gate_mod.PassThroughGate(card).decide()
        self.assertEqual(decision.n_required, card.n_required)

    def test_passthrough_exposes_the_same_interface(self) -> None:
        for name in ("toggle", "decide", "open", "issue_token", "consume_token"):
            self.assertTrue(hasattr(gate_mod.PassThroughGate(_card()), name))


class CliTests(unittest.TestCase):
    def test_selftest_covers_block_unlock_and_bypass(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "govern.gate", "--selftest"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("blocked", proc.stdout)
        self.assertIn("unlocked", proc.stdout)
        self.assertIn("bypass refused", proc.stdout)


if __name__ == "__main__":
    unittest.main()
