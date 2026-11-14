"""Mandatory confirmation gate (SPEC M6 / PLAN milestone M4).

The gate is a small state machine, deliberately the only place that can say
"yes, generate". It has no public attribute that flips the answer, no way to
inherit confirmations, and it validates the card it is handed so a card that
understates what is required is rejected outright.

``PassThroughGate`` is the ``C0`` baseline: identical interface, never blocks,
so both conditions write the same event schema (SPEC M6 acceptance 4).
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from govern import card as card_mod
from govern import config, impact, tasks


@dataclass(frozen=True)
class GateDecision:
    blocked: bool
    confirmed: bool
    n_required: int
    n_confirmed: int


class Gate:
    """Blocks until every required card item has been confirmed."""

    def __init__(self, card: card_mod.Card, clock: Callable[[], float] | None = None) -> None:
        known = {item.item_id for item in card.items}
        unknown = set(card.required_ids) - known
        if unknown:
            raise ValueError(f"required ids not on the card: {sorted(unknown)}")
        if len(card.required_ids) != card.n_required:
            raise ValueError(
                f"card says {card.n_required} required but lists {len(card.required_ids)}"
            )
        if card.n_required > card.n_items:
            raise ValueError(f"card requires {card.n_required} of {card.n_items} items")

        self._card = card
        self._known = known
        self._required = set(card.required_ids)
        self._checked: set[str] = set()
        self._clock = clock or time.monotonic
        self._last = self._clock()
        self._token: str | None = None
        self._issued = 0

    # -- interaction -----------------------------------------------------
    def toggle(self, item_id: str) -> tuple[bool, int]:
        """Flip one checkbox; return ``(now_checked, dwell_ms_since_previous)``."""
        if item_id not in self._known:
            raise KeyError(f"unknown card item: {item_id}")
        now = self._clock()
        dwell_ms = int(round((now - self._last) * 1000))
        self._last = now
        self._token = None  # any change invalidates a live authorisation
        if item_id in self._checked:
            self._checked.discard(item_id)
            return False, dwell_ms
        self._checked.add(item_id)
        return True, dwell_ms

    # -- decisions -------------------------------------------------------
    def decide(self) -> GateDecision:
        n_confirmed = len(self._checked & self._required)
        blocked = n_confirmed < self._card.n_required
        return GateDecision(
            blocked=blocked,
            confirmed=not blocked,
            n_required=self._card.n_required,
            n_confirmed=n_confirmed,
        )

    def open(self) -> bool:
        """True when generation is currently allowed."""
        return not self.decide().blocked

    # -- one-shot authorisation -----------------------------------------
    def issue_token(self) -> str | None:
        """Return a token for one generation, or ``None`` while blocked."""
        if not self.open():
            self._token = None
            return None
        if self._token is None:
            self._issued += 1
            self._token = f"{self._card.card_id}:{self._issued}"
        return self._token

    def consume_token(self) -> bool:
        """Spend the live token. A second call needs a re-issued token."""
        if self._token is None:
            return False
        self._token = None
        return True


class PassThroughGate(Gate):
    """``C0`` baseline: same interface, never blocks (SPEC M6 acceptance 4)."""

    def decide(self) -> GateDecision:
        return GateDecision(
            blocked=False,
            confirmed=True,
            n_required=self._card.n_required,
            n_confirmed=self._card.n_required,
        )


def _selftest() -> int:
    cfg = config.load()
    loaded = tasks.load_index(Path("corpus"))
    if not loaded:
        print("no tasks in corpus/")
        return 1

    failures = 0
    for task in loaded:
        result = impact.analyze(task.repo, task.intent)
        card = card_mod.build(result, task, "C1")
        gate = Gate(card, clock=time.monotonic)

        if not gate.decide().blocked:
            print(f"FAIL {task.task_id}: a fresh gate must block")
            failures += 1
            continue
        for item_id in card.required_ids[:-1]:
            gate.toggle(item_id)
        if not gate.decide().blocked:
            print(f"FAIL {task.task_id}: blocked expected with one item left")
            failures += 1
        gate.toggle(card.required_ids[-1])
        if gate.decide().blocked:
            print(f"FAIL {task.task_id}: gate should be unlocked when all are confirmed")
            failures += 1

    sample = loaded[0]
    sample_card = card_mod.build(impact.analyze(sample.repo, sample.intent), sample, "C1")
    print(f"  {sample.task_id}: blocked with 0/{sample_card.n_required}, unlocked at {sample_card.n_required}/{sample_card.n_required}")

    forged = card_mod.Card(
        card_id=sample_card.card_id,
        version=sample_card.version,
        items=sample_card.items,
        required_ids=sample_card.required_ids[:-1],
        n_items=sample_card.n_items,
        n_required=sample_card.n_required,
    )
    try:
        Gate(forged)
    except ValueError:
        print("  bypass refused: a card that hides a required item is rejected")
    else:
        print("FAIL: forged card was accepted")
        failures += 1

    passthrough = PassThroughGate(sample_card)
    if passthrough.decide().blocked:
        print("FAIL: C0 passthrough must never block")
        failures += 1
    print(f"  C0 passthrough: blocked={passthrough.decide().blocked} on the same interface")

    status = "ok" if not failures else "FAIL"
    print(
        f"{status}: {len(loaded)} cards, blocked until every item is confirmed, "
        f"C0 passthrough, min dwell {cfg.mech_dwell_ms} ms"
    )
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m govern.gate")
    parser.add_argument("--selftest", action="store_true", help="replay the gate invariant on corpus/")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
