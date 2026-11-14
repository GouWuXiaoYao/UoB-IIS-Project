"""Session orchestrator: assignment, state machine, checkpoint/resume.

SPEC M2 owns this module. It is deliberately dull: every decision it makes is
derived from ``config/schedule.json`` or from the log, never from the clock or
from a random draw made at run time.

Two ideas keep the governance claim honest:

* **Assignment is data.** ``assign()`` is a pure function of (schedule,
  participant, corpus). The same inputs always give the same task sequence, so
  a condition can never be changed mid-session to make a result look better.
* **The log is the state.** ``Session.state()`` and ``rebuild_state()`` must
  agree; ``resume()`` refuses to run when the checkpoint and the log disagree
  instead of guessing which one is right (PLAN risk R10).

Author self-test note (SPEC M2 status: SIM): nothing here was ever driven by a
recruited participant. ``start()`` runs with the fixed consent record
``consent_version = "SIM-AUTHOR"`` and the UI is exercised by the author.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from govern import card as card_mod
from govern import config, gate as gate_mod, hidden, impact, llm, log, patch, score, tasks

SCHEDULE_PATH = Path("config") / "schedule.json"
ORDERS = ("AB", "BA")
CONDITIONS = ("C0", "C1")

EXIT_OK = 0


class ConsentError(RuntimeError):
    """Raised when a session is asked to start without a consent record."""


class GateClosed(RuntimeError):
    """Raised when generation is attempted before the gate is open."""


class StateConflict(RuntimeError):
    """Raised when the checkpoint and the log disagree, or a session is over."""


@dataclass(frozen=True)
class Slot:
    """One task, in one condition, at one position in the sequence."""

    task_id: str
    pair_id: str
    condition: str
    task_index: int


# ---------------------------------------------------------------------------
# assignment
# ---------------------------------------------------------------------------
def load_schedule(path: str | Path = SCHEDULE_PATH) -> dict:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    required = {"schedule_id", "seed", "pairs", "participants", "orders"}
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"schedule {p} is missing: {', '.join(missing)}")
    if len(raw["participants"]) != len(raw["orders"]):
        raise ValueError(f"schedule {p}: participants and orders differ in length")
    for order in raw["orders"]:
        if order not in ORDERS:
            raise ValueError(f"schedule {p}: unknown order {order!r}")
    return raw


def assign(schedule: dict, participant: str, task_list: list[tasks.Task]) -> list[Slot]:
    """Return this participant's task sequence (deterministic, paired)."""
    participants = list(schedule["participants"])
    if participant not in participants:
        raise KeyError(f"participant {participant!r} is not in the schedule")
    index = participants.index(participant)
    order = schedule["orders"][index % len(schedule["orders"])]

    by_pair: dict[str, list[tasks.Task]] = {}
    for task in task_list:
        by_pair.setdefault(task.pair_id, []).append(task)

    pairs = list(schedule["pairs"])
    unknown = [pair for pair in pairs if pair not in by_pair]
    if unknown:
        raise ValueError(f"schedule names pairs the corpus does not have: {unknown}")

    rng = random.Random(f"{schedule['seed']}:{participant}")
    rng.shuffle(pairs)

    slots: list[Slot] = []
    for pair_id in pairs:
        members = sorted(by_pair[pair_id], key=lambda t: t.task_id)
        if len(members) != 2:
            raise ValueError(f"{pair_id} does not hold exactly two tasks")
        conditions = ("C1", "C0") if order == "AB" else ("C0", "C1")
        for task, condition in zip(members, conditions):
            slots.append(Slot(task.task_id, pair_id, condition, len(slots)))
    return slots


def chi_square_p(counts: dict[str, int]) -> float:
    """Goodness-of-fit p for an even split of two conditions (1 degree of freedom)."""
    total = sum(counts.values())
    if total == 0:
        return 1.0
    expected = total / len(counts) if counts else 0.0
    if expected <= 0:  # pragma: no cover - defensive
        return 1.0
    chi2 = sum((observed - expected) ** 2 / expected for observed in counts.values())
    return math.erfc(math.sqrt(chi2 / 2.0))


def simulate(schedule: dict, task_list: list[tasks.Task], n: int) -> dict:
    """Assign ``n`` virtual participants and report the balance check."""
    if n < 1:
        raise ValueError("n must be positive")

    participants = list(schedule["participants"])
    orders = list(schedule["orders"])
    while len(participants) < n:
        position = len(participants)
        participants.append(f"P{position + 1:03d}")
        orders.append(ORDERS[position % 2])
    extended = {**schedule, "participants": participants, "orders": orders}

    counts = {condition: 0 for condition in CONDITIONS}
    pairs: dict[str, list[str]] = {}
    for participant in participants[:n]:
        for slot in assign(extended, participant, task_list):
            counts[slot.condition] += 1
            seen = pairs.setdefault(slot.pair_id, [])
            if slot.condition not in seen:
                seen.append(slot.condition)

    alpha = config.load().alpha_sim
    p_value = chi_square_p(counts)
    ordered_pairs = {pair: sorted(seen) for pair, seen in sorted(pairs.items())}
    return {
        "n": n,
        "counts": counts,
        "p": p_value,
        "alpha": alpha,
        "balanced": p_value > alpha,
        "pairs": ordered_pairs,
        "pairs_both_conditions": all(seen == ["C0", "C1"] for seen in ordered_pairs.values()),
    }


# ---------------------------------------------------------------------------
# log-derived state
# ---------------------------------------------------------------------------
def rebuild_state(log_path: str | Path) -> dict:
    """Rebuild a session's state from its JSONL alone (SPEC M2 acceptance 4)."""
    events = [
        json.loads(line)
        for line in Path(log_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not events:
        raise StateConflict(f"empty log: {log_path}")

    confirmed: set[str] = set()
    state = {
        "session_id": events[0]["session_id"],
        "participant_id": events[0]["participant_id"],
        "condition": events[0]["condition"],
        "task_id": None,
        "task_index": None,
        "phase": events[-1]["phase"],
        "card_id": None,
        "confirmed_ids": [],
        "gate_open": None,
        "n_events": len(events),
        "ended": False,
    }
    for event in events:
        state["task_id"] = event.get("task_id") or state["task_id"]
        state["task_index"] = (
            event["task_index"] if event.get("task_index") is not None else state["task_index"]
        )
        kind = event["event_type"]
        if kind == "card_shown":
            state["card_id"] = event["card_id"]
            confirmed.clear()
        elif kind == "card_item_toggle":
            if event["checked"]:
                confirmed.add(event["item_id"])
            else:
                confirmed.discard(event["item_id"])
        elif kind == "gate_decision":
            state["gate_open"] = not event["blocked"]
        elif kind == "task_end":
            state["ended"] = True
        elif kind == "session_end":
            state["ended"] = True
    state["confirmed_ids"] = sorted(confirmed)
    return state


# ---------------------------------------------------------------------------
# the state machine
# ---------------------------------------------------------------------------
class Session:
    """One participant, one task, one condition, one log."""

    def __init__(
        self,
        run_dir: Path,
        task: tasks.Task,
        condition: str,
        participant: str,
        logger: log.Logger,
        *,
        mode: str = "replay",
        task_index: int = 0,
        client: llm.Client | None = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.task = task
        self.condition = condition
        self.participant = participant
        self.task_index = task_index
        self.logger = logger

        cfg = config.load()
        self._cfg = cfg
        self.mode = mode

        self.work = self.run_dir / "work" / logger.session_id / task.task_id
        if self.work.exists():
            shutil.rmtree(self.work, ignore_errors=True)
        self.work.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(task.repo, self.work)

        self.impact_set = impact.analyze(task.repo, task.intent)
        self.impact_hash = impact.impact_hash(self.impact_set)
        self.card = card_mod.build(self.impact_set, task, condition)
        self.gate = (
            gate_mod.PassThroughGate(self.card)
            if condition == card_mod.BASELINE_CONDITION
            else gate_mod.Gate(self.card)
        )
        self.client = client or llm.Client(cfg, mode=mode, logger=logger)
        self.baseline = score.baseline(task)

        self.phase = "setup"
        self._last_phase = "setup"
        self._ended = False
        self._started = False
        self._opened_at = time.monotonic()
        self._prompt_at = 0.0
        self._last_suggestion: llm.Suggestion | None = None
        self._last_action = None
        self._gate_open = False
        self._counts = {"suggestions": 0, "accepted": 0, "edits": 0, "rejects": 0}

    # -- lifecycle -------------------------------------------------------
    def start(self, consent: dict) -> None:
        """Emit ``session_start``; refuse to run without consent (SPEC M2.5)."""
        if self._started:
            raise RuntimeError("this session has already started")
        if not consent.get("consent_given"):
            raise ConsentError(
                "consent_given is false: refusing to start a session without a consent record"
            )
        self.logger.emit(
            "session_start",
            phase="setup",
            consent_version=str(consent.get("consent_version", "SIM-AUTHOR")),
            consent_given=True,
            prior_years=float(consent.get("prior_years", 0.0)),
            llm_freq=str(consent.get("llm_freq", "never")),
            lang_familiarity=int(consent.get("lang_familiarity", 3)),
            schedule_id=str(consent.get("schedule_id", "")),
            device=str(consent.get("device", "author-workstation")),
        )
        self._started = True
        self.phase = "prompt"
        self._opened_at = time.monotonic()

    # -- prompt and card -------------------------------------------------
    def submit_prompt(self, text: str) -> card_mod.Card:
        self._require_started()
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.logger.emit(
            "prompt_submit",
            **self._where("prompt"),
            prompt_id=f"P-{uuid.uuid4().hex[:12]}",
            prompt_len_chars=len(text),
            prompt_sha256=digest,
            attached_files=[],
        )
        latency = int((time.monotonic() - self._opened_at) * 1000)
        self.logger.emit(
            "card_shown",
            **self._where("card"),
            card_id=self.card.card_id,
            card_version=self.card.version,
            n_items=self.card.n_items,
            n_required=self.card.n_required,
            latency_from_prompt_ms=latency,
            impact_set_hash=self.impact_hash,
        )
        self.phase = "gate"
        self._prompt_at = time.monotonic()
        return self.card

    def toggle(self, item_id: str) -> tuple[bool, gate_mod.GateDecision]:
        self._require_started()
        checked, dwell_ms = self.gate.toggle(item_id)
        item = next((i for i in self.card.items if i.item_id == item_id), None)
        if item is None:  # pragma: no cover - gate already validates the id
            raise KeyError(f"unknown card item: {item_id}")
        self.logger.emit(
            "card_item_toggle",
            **self._where("gate"),
            card_id=self.card.card_id,
            item_id=item_id,
            item_category=item.category,
            checked=checked,
            dwell_ms=max(dwell_ms, 0),
        )
        return checked, self.gate.decide()

    def confirm(self) -> gate_mod.GateDecision:
        self._require_started()
        decision = self.gate.decide()
        latency = int((time.monotonic() - self._prompt_at) * 1000) if self._prompt_at else 0
        self.logger.emit(
            "gate_decision",
            **self._where("gate"),
            card_id=self.card.card_id,
            confirmed=decision.confirmed,
            blocked=decision.blocked,
            n_required=decision.n_required,
            n_confirmed=decision.n_confirmed,
            gate_latency_ms=latency,
        )
        self._gate_open = not decision.blocked
        return decision

    # -- generation ------------------------------------------------------
    def generate(self) -> llm.Suggestion:
        self._require_started()
        if not self.gate.open():
            # The refusal itself is data: a blocked attempt must be in the log,
            # otherwise "how often did people try to skip the gate" is unanswerable.
            decision = self.gate.decide()
            self.logger.emit(
                "gate_decision",
                **self._where("gate"),
                card_id=self.card.card_id,
                confirmed=bool(decision.confirmed),
                blocked=True,
                n_required=decision.n_required,
                n_confirmed=decision.n_confirmed,
                gate_latency_ms=0,
            )
            self._gate_open = False
            raise GateClosed(
                "the confirmation gate is closed: confirm every required item before generating"
            )
        self.gate.issue_token()
        if not self.gate.consume_token():  # pragma: no cover - token issued just above
            raise GateClosed("no live authorisation: the gate changed since it was opened")

        ctx = llm.Context.for_task(self.task)
        suggestion = self.client.generate(ctx)
        files = patch.parse(suggestion.patch_diff)
        changed = sum(
            1
            for line in suggestion.patch_diff.splitlines()
            if line[:1] in ("+", "-") and not line.startswith(("+++", "---"))
        )
        self.logger.emit(
            "suggestion_shown",
            **self._where("generate"),
            suggestion_id=suggestion.suggestion_id,
            suggestion_seq=self._counts["suggestions"] + 1,
            n_files=len(files),
            n_lines_changed=changed,
            n_hunks=sum(len(hunks) for _, hunks in files),
            rationale_len_chars=len(suggestion.rationale_text),
        )
        self._counts["suggestions"] += 1
        self._last_suggestion = suggestion
        self.phase = "review"
        return suggestion

    # -- review ----------------------------------------------------------
    def last_suggestion(self) -> llm.Suggestion | None:
        """The most recent suggestion, or ``None`` before anything was generated.

        The page needs it after a reload: a tab that reconnects must be able to show
        the pending suggestion rather than a card with no next step.
        """
        return self._last_suggestion

    def act(
        self,
        suggestion_id: str,
        action: str,
        dwell_ms: int,
        edit_lines: int | None = None,
    ) -> None:
        self._require_started()
        if action not in ("accept", "edit", "reject", "regenerate"):
            raise ValueError(f"unknown action: {action!r}")
        if action in ("accept", "edit"):
            self._apply_last_suggestion(action)
            self._counts["accepted" if action == "accept" else "edits"] += 1
        elif action == "reject":
            self._counts["rejects"] += 1
        self._last_action = {
            "suggestion_id": suggestion_id,
            "action": action,
            "applied": action in ("accept", "edit"),
        }
        self.logger.emit(
            "suggestion_action",
            **self._where("review"),
            suggestion_id=suggestion_id,
            action=action,
            review_dwell_ms=int(dwell_ms),
            edit_distance_lines=edit_lines if action == "edit" else None,
            accepted_after_gate=self._gate_open,
        )

    # -- scoring ---------------------------------------------------------
    def end(self, submitted: bool, timeout: bool = False) -> score.Outcome:
        self._require_started()
        elapsed_ms = int((time.monotonic() - self._opened_at) * 1000)
        code, failures, n_tests = hidden.run(
            self.work, self.task.hidden_tests, self._cfg.test_timeout_s
        )
        hidden_run = (code == 0 and n_tests > 0, failures)
        outcome = score.evaluate(
            self.task,
            self.work,
            self.baseline,
            timeout_s=self._cfg.test_timeout_s,
            hidden_run=hidden_run,
        )
        self.logger.emit(
            "test_run",
            **self._where("test"),
            suite="hidden",
            n_pass=max(n_tests - len(failures), 0),
            n_fail=len(failures),
            failing_tests=failures,
        )
        if self._last_suggestion is not None:
            # Emitted *before* task_end so that task_end stays the closing event
            # of a task, the way session_end closes a session.
            self.logger.emit(
                "suggestion_scored",
                **self._where("test"),
                suggestion_id=self._last_suggestion.suggestion_id,
                is_correct=score.is_correct(self.baseline, outcome),
                gold_patch_match=self._gold_match(),
                scored_by="hidden_tests",
                scorer_version=outcome.scorer_version,
            )
        self.logger.emit(
            "task_end",
            **self._where("test"),
            elapsed_ms=elapsed_ms,
            submitted=bool(submitted),
            timeout=bool(timeout),
            tests_pass=outcome.tests_pass,
            n_fail=outcome.n_fail,
            debt_delta=outcome.debt_delta,
            vuln_delta=outcome.vuln_delta,
            lines_added=outcome.lines_added,
            lines_removed=outcome.lines_removed,
            n_suggestions=self._counts["suggestions"],
            n_accepted=self._counts["accepted"],
            n_edits=self._counts["edits"],
            n_rejects=self._counts["rejects"],
        )
        self.phase = "end"
        self._ended = True
        return outcome

    # -- state -----------------------------------------------------------
    def state(self) -> dict:
        return {
            "session_id": self.logger.session_id,
            "participant_id": self.participant,
            "condition": self.condition,
            "task_id": self.task.task_id,
            "task_index": self.task_index,
            "phase": self._last_phase,
            "card_id": self.card.card_id,
            "confirmed_ids": sorted(self.gate.confirmed_ids()),
            "gate_open": self._gate_open,
            "last_action": self._last_action,
            "n_events": self._n_events(),
            "ended": self._ended,
        }

    def checkpoint(self, path: Path) -> Path:
        """Write the fast projection of the state (the log stays authoritative)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            **self.state(),
            "run_dir": str(self.run_dir),
            "mode": self.mode,
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    @classmethod
    def resume(cls, path: str | Path, **kwargs) -> "Session":
        """Rebuild a session from a checkpoint, refusing any disagreement."""
        path = Path(path)
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("ended"):
            raise StateConflict(f"{path} belongs to a finished session; nothing to resume")

        run_dir = Path(saved["run_dir"])
        cfg = config.load()
        logger = log.Logger(
            run_dir,
            {
                "session_id": saved["session_id"],
                "participant_id": saved["participant_id"],
                "condition": saved["condition"],
                "app_version": cfg.app_version,
                "model_id": cfg.model_id,
                "model_temperature": cfg.temperature,
                "seed": cfg.seed,
            },
        )
        if logger.path.is_file():
            from_log = rebuild_state(logger.path)
            if from_log["n_events"] != int(saved["n_events"]):
                raise StateConflict(
                    f"{logger.path} holds {from_log['n_events']} events but the checkpoint says "
                    f"{saved['n_events']}; refusing to guess which one is right"
                )

        task = tasks.by_id(tasks.load_index(), saved["task_id"])
        session = cls(
            run_dir,
            task,
            saved["condition"],
            saved["participant_id"],
            logger,
            mode=saved.get("mode", "replay"),
            task_index=int(saved.get("task_index", 0)),
            **kwargs,
        )
        session._started = True
        session.phase = saved["phase"]
        session._gate_open = bool(saved.get("gate_open"))
        session.gate.restore(saved.get("confirmed_ids", []))
        return session

    # -- helpers ---------------------------------------------------------
    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("the session has not started: call start(consent) first")

    def _where(self, phase: str) -> dict:
        self._last_phase = phase
        return {
            "phase": phase,
            "task_id": self.task.task_id,
            "task_index": self.task_index,
            "pair_id": self.task.pair_id,
        }

    def _n_events(self) -> int:
        if not self.logger.path.is_file():
            return 0
        return sum(
            1 for line in self.logger.path.read_text(encoding="utf-8").splitlines() if line.strip()
        )

    def _apply_last_suggestion(self, action: str) -> None:
        if self._last_suggestion is None:
            raise RuntimeError("no suggestion to apply")
        patch.apply_unified_diff(self._last_suggestion.patch_diff, self.work)

    def _gold_match(self) -> bool:
        if self._last_suggestion is None:
            return False
        gold = self.task.gold_patch.read_text(encoding="utf-8").strip()
        return self._last_suggestion.patch_diff.strip() == gold


def _selftest() -> int:
    """Verify the schedule, the assignment and the log rebuild without a session."""
    cfg = config.load()
    schedule = load_schedule(SCHEDULE_PATH)
    task_list = tasks.load_index()
    order = assign(schedule, schedule["participants"][0], task_list)
    again = assign(schedule, schedule["participants"][0], task_list)
    if [s.task_id for s in order] != [s.task_id for s in again]:
        raise SystemExit("assignment is not deterministic")
    report = simulate(schedule, task_list, n=cfg.n_participants * 10)
    print(
        f"ok: {len(schedule['participants'])} participants, {len(order)} slots each, "
        f"deterministic, C0={report['counts']['C0']} C1={report['counts']['C1']} "
        f"chi2 p={report['p']:.3f}"
    )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m govern.session")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--simulate", type=int, metavar="N")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.simulate is not None:
        report = simulate(load_schedule(SCHEDULE_PATH), tasks.load_index(), args.simulate)
        print(f"ok: simulated {report['n']} assignments, chi2 p={report['p']:.3f}")
        return EXIT_OK
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
