"""Acceptance tests for the session orchestrator (SPEC M2 / PLAN milestone M8)."""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from govern import config, log, session, tasks
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
CONFIG = config.load(ROOT / "config" / "config.json")
TASKS = tasks.load_index(ROOT / "corpus")
SCHEDULE_PATH = ROOT / "config" / "schedule.json"

CONSENT = {
    "consent_version": "SIM-AUTHOR",
    "consent_given": True,
    "prior_years": 0.0,
    "llm_freq": "never",
    "lang_familiarity": 5,
    "schedule_id": "SCH-01",
    "device": "author-workstation",
}


def _logger(run_dir: Path, participant: str = "P01", condition: str = "C1") -> log.Logger:
    return log.Logger(
        run_dir,
        {
            "session_id": f"S-{participant}-{condition}",
            "participant_id": participant,
            "condition": condition,
            "app_version": CONFIG.app_version,
            "model_id": CONFIG.model_id,
            "model_temperature": CONFIG.temperature,
            "seed": CONFIG.seed,
        },
    )


def _session(run_dir: Path, task_id: str = "T-L01a", condition: str = "C1", **kwargs) -> session.Session:
    return session.Session(
        run_dir,
        tasks.by_id(TASKS, task_id),
        condition,
        "P01",
        _logger(run_dir, condition=condition),
        **kwargs,
    )


def _events(logger: log.Logger) -> list[dict]:
    return [json.loads(line) for line in logger.path.read_text(encoding="utf-8").splitlines() if line]


class ScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedule = session.load_schedule(SCHEDULE_PATH)

    def test_the_shipped_schedule_covers_every_pair(self):
        pairs = {task.pair_id for task in TASKS}
        self.assertEqual(set(self.schedule["pairs"]), pairs)

    def test_assignment_is_deterministic(self):
        first = session.assign(self.schedule, "P01", TASKS)
        second = session.assign(self.schedule, "P01", TASKS)
        self.assertEqual(
            [(s.task_id, s.condition, s.task_index) for s in first],
            [(s.task_id, s.condition, s.task_index) for s in second],
        )

    def test_each_participant_sees_every_task_exactly_once(self):
        slots = session.assign(self.schedule, "P03", TASKS)
        self.assertEqual(sorted(s.task_id for s in slots), sorted(t.task_id for t in TASKS))

    def test_task_index_is_sequential_from_zero(self):
        slots = session.assign(self.schedule, "P02", TASKS)
        self.assertEqual([s.task_index for s in slots], list(range(len(TASKS))))

    def test_every_pair_appears_in_both_conditions(self):
        seen: dict[str, set[str]] = {}
        for participant in self.schedule["participants"]:
            for slot in session.assign(self.schedule, participant, TASKS):
                seen.setdefault(slot.pair_id, set()).add(slot.condition)
        for pair_id, conditions in seen.items():
            self.assertEqual(conditions, {"C0", "C1"}, pair_id)

    def test_each_task_runs_in_one_condition_only(self):
        for participant in self.schedule["participants"]:
            slots = session.assign(self.schedule, participant, TASKS)
            by_pair: dict[str, set[str]] = {}
            for slot in slots:
                by_pair.setdefault(slot.pair_id, set()).add(slot.condition)
            for pair_id, conditions in by_pair.items():
                self.assertEqual(len(conditions), 2, pair_id)

    def test_pair_order_varies_between_participants(self):
        sequences = {
            tuple(s.pair_id for s in session.assign(self.schedule, participant, TASKS))
            for participant in self.schedule["participants"]
        }
        self.assertGreater(len(sequences), 1, "every participant got the same block order")

    def test_an_unknown_participant_is_rejected(self):
        with self.assertRaises(KeyError):
            session.assign(self.schedule, "P99", TASKS)

    def test_slot_carries_the_pair_and_the_condition(self):
        slot = session.assign(self.schedule, "P01", TASKS)[0]
        self.assertIn(slot.condition, ("C0", "C1"))
        self.assertTrue(slot.pair_id.startswith("PAIR-"))


class SimulateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedule = session.load_schedule(SCHEDULE_PATH)

    def test_chi_square_of_a_perfect_split_is_close_to_one(self):
        self.assertGreater(session.chi_square_p({"C0": 50, "C1": 50}), 0.99)

    def test_chi_square_detects_an_unbalanced_split(self):
        self.assertLess(session.chi_square_p({"C0": 90, "C1": 10}), 0.001)

    def test_chi_square_matches_the_closed_form_for_one_degree_of_freedom(self):
        # 60/40 of 100 -> chi2 = (10^2)/50 + (10^2)/50 = 4, p = erfc(sqrt(2))
        expected = math.erfc(math.sqrt(4.0 / 2))
        self.assertAlmostEqual(session.chi_square_p({"C0": 60, "C1": 40}), expected, places=9)

    def test_simulation_is_balanced(self):
        report = session.simulate(self.schedule, TASKS, n=100)
        self.assertEqual(report["n"], 100)
        self.assertGreater(report["p"], CONFIG.alpha_sim)
        self.assertTrue(report["balanced"])

    def test_simulation_sees_both_conditions_for_every_pair(self):
        report = session.simulate(self.schedule, TASKS, n=100)
        self.assertTrue(report["pairs_both_conditions"], report["pairs"])
        for pair_id, conditions in report["pairs"].items():
            self.assertEqual(set(conditions), {"C0", "C1"}, pair_id)

    def test_simulation_is_deterministic(self):
        first = session.simulate(self.schedule, TASKS, n=40)
        second = session.simulate(self.schedule, TASKS, n=40)
        self.assertEqual(first, second)

    def test_simulation_counts_every_slot(self):
        report = session.simulate(self.schedule, TASKS, n=10)
        self.assertEqual(sum(report["counts"].values()), 10 * len(TASKS))


class ConsentTests(unittest.TestCase):
    def test_a_session_without_consent_refuses_to_start(self):
        with scratch_dir("consent") as tmp:
            sess = _session(tmp)
            with self.assertRaises(session.ConsentError) as ctx:
                sess.start({**CONSENT, "consent_given": False})
            self.assertIn("consent", str(ctx.exception).lower())
            self.assertFalse(sess.logger.path.exists())

    def test_a_started_session_records_the_consent(self):
        with scratch_dir("start") as tmp:
            sess = _session(tmp)
            sess.start(CONSENT)
            start = _events(sess.logger)[0]
            self.assertEqual(start["event_type"], "session_start")
            self.assertEqual(start["schedule_id"], "SCH-01")
            self.assertEqual(start["consent_version"], "SIM-AUTHOR")
            self.assertTrue(start["consent_given"])

    def test_starting_twice_is_rejected(self):
        with scratch_dir("twice") as tmp:
            sess = _session(tmp)
            sess.start(CONSENT)
            with self.assertRaises(RuntimeError):
                sess.start(CONSENT)


class FlowTests(unittest.TestCase):
    def _started(self, tmp: Path, condition: str = "C1") -> session.Session:
        sess = _session(tmp, condition=condition)
        sess.start(CONSENT)
        return sess

    def test_submit_prompt_logs_the_prompt_and_the_card(self):
        with scratch_dir("flow") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor the total calculation.")
            shown = _events(sess.logger)[-1]
            self.assertEqual(shown["event_type"], "card_shown")
            self.assertEqual(shown["n_items"], len(card.items))
            self.assertEqual(shown["n_required"], card.n_required)
            self.assertEqual(shown["impact_set_hash"], sess.impact_hash)

    def test_the_prompt_body_is_not_logged_only_its_hash(self):
        with scratch_dir("nosecret") as tmp:
            sess = self._started(tmp)
            text = "Refactor the total calculation please."
            sess.submit_prompt(text)
            raw = sess.logger.path.read_text(encoding="utf-8")
            self.assertNotIn("Refactor the total", raw)
            submitted = _events(sess.logger)[-2]
            self.assertEqual(submitted["prompt_len_chars"], len(text))
            self.assertEqual(len(submitted["prompt_sha256"]), 64)

    def test_the_baseline_condition_shows_an_empty_card(self):
        with scratch_dir("c0") as tmp:
            sess = self._started(tmp, condition="C0")
            card = sess.submit_prompt("Refactor.")
            self.assertEqual(card.n_items, 0)
            self.assertEqual(card.n_required, 0)
            self.assertEqual(_events(sess.logger)[-1]["n_items"], 0)

    def test_toggling_logs_every_checkbox(self):
        with scratch_dir("toggle") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor.")
            checked, decision = sess.toggle(card.items[0].item_id)
            self.assertTrue(checked)
            self.assertTrue(decision.blocked)
            event = _events(sess.logger)[-1]
            self.assertEqual(event["event_type"], "card_item_toggle")
            self.assertTrue(event["checked"])
            self.assertIsInstance(event["dwell_ms"], int)

    def test_generation_stays_closed_until_every_item_is_confirmed(self):
        with scratch_dir("closed") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor.")
            if card.n_required == 0:
                self.skipTest("baseline has no gate")
            with self.assertRaises(session.GateClosed):
                sess.generate()

    def test_a_partial_confirmation_is_logged_as_blocked(self):
        with scratch_dir("blocked") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor.")
            if card.n_required < 2:
                self.skipTest("needs at least two required items")
            sess.toggle(card.items[0].item_id)
            decision = sess.confirm()
            self.assertTrue(decision.blocked)
            event = _events(sess.logger)[-1]
            self.assertEqual(event["event_type"], "gate_decision")
            self.assertTrue(event["blocked"])
            self.assertEqual(event["n_confirmed"], 1)

    def test_confirming_every_item_opens_the_gate(self):
        with scratch_dir("open") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor.")
            for item in card.items:
                sess.toggle(item.item_id)
            decision = sess.confirm()
            self.assertFalse(decision.blocked)
            self.assertFalse(_events(sess.logger)[-1]["blocked"])

    def test_generate_logs_one_request_and_one_suggestion(self):
        with scratch_dir("generate") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor.")
            for item in card.items:
                sess.toggle(item.item_id)
            sess.confirm()
            suggestion = sess.generate()
            tail = [e["event_type"] for e in _events(sess.logger)[-2:]]
            self.assertEqual(tail, ["generation_request", "suggestion_shown"])
            self.assertTrue(suggestion.patch_diff)
            shown = _events(sess.logger)[-1]
            self.assertEqual(shown["n_files"], len(suggestion.patch_diff.split("--- ")) - 1)

    def test_act_logs_the_review_action(self):
        with scratch_dir("act") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor.")
            for item in card.items:
                sess.toggle(item.item_id)
            sess.confirm()
            suggestion = sess.generate()
            sess.act(suggestion.suggestion_id, "accept", dwell_ms=1500)
            event = _events(sess.logger)[-1]
            self.assertEqual(event["event_type"], "suggestion_action")
            self.assertEqual(event["action"], "accept")
            self.assertEqual(event["review_dwell_ms"], 1500)
            self.assertTrue(event["accepted_after_gate"])

    def test_end_logs_the_test_run_the_task_end_and_the_score(self):
        with scratch_dir("end") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor.")
            for item in card.items:
                sess.toggle(item.item_id)
            sess.confirm()
            suggestion = sess.generate()
            sess.act(suggestion.suggestion_id, "accept", dwell_ms=1500)
            sess.end(submitted=True)
            kinds = [e["event_type"] for e in _events(sess.logger)[-3:]]
            self.assertEqual(kinds, ["test_run", "task_end", "suggestion_scored"])

    def test_every_emitted_event_passes_the_schema_validator(self):
        with scratch_dir("schema") as tmp:
            sess = self._started(tmp)
            card = sess.submit_prompt("Refactor.")
            for item in card.items:
                sess.toggle(item.item_id)
            sess.confirm()
            suggestion = sess.generate()
            sess.act(suggestion.suggestion_id, "accept", dwell_ms=900)
            sess.end(submitted=True)
            for event in _events(sess.logger):
                self.assertEqual(log.validate(event), [], event["event_type"])


class ResumeTests(unittest.TestCase):
    def _midway(self, tmp: Path) -> session.Session:
        sess = _session(tmp)
        sess.start(CONSENT)
        card = sess.submit_prompt("Refactor.")
        sess.toggle(card.items[0].item_id)
        return sess

    def test_state_can_be_rebuilt_from_the_log(self):
        with scratch_dir("rebuild") as tmp:
            sess = self._midway(tmp)
            rebuilt = session.rebuild_state(sess.logger.path)
            self.assertEqual(rebuilt["card_id"], sess.state()["card_id"])
            self.assertEqual(rebuilt["confirmed_ids"], sess.state()["confirmed_ids"])
            self.assertEqual(rebuilt["phase"], sess.state()["phase"])

    def test_checkpoint_then_resume_continues_the_sequence(self):
        with scratch_dir("resume") as tmp:
            sess = self._midway(tmp)
            state_path = tmp / "state" / "S.json"
            sess.checkpoint(state_path)
            before = len(_events(sess.logger))

            resumed = session.Session.resume(state_path)
            self.assertEqual(resumed.state()["confirmed_ids"], sess.state()["confirmed_ids"])
            card = resumed.card
            for item in card.items:
                if item.item_id not in resumed.state()["confirmed_ids"]:
                    resumed.toggle(item.item_id)
            resumed.confirm()
            resumed.generate()
            resumed.end(submitted=True)

            events = _events(resumed.logger)
            self.assertGreater(len(events), before)
            seqs = [e["seq"] for e in events]
            self.assertEqual(seqs, list(range(1, len(events) + 1)))
            ids = [e["event_id"] for e in events]
            self.assertEqual(len(ids), len(set(ids)))

    def test_resume_refuses_a_finished_session(self):
        with scratch_dir("finished") as tmp:
            sess = _session(tmp)
            sess.start(CONSENT)
            card = sess.submit_prompt("Refactor.")
            for item in card.items:
                sess.toggle(item.item_id)
            sess.confirm()
            suggestion = sess.generate()
            sess.act(suggestion.suggestion_id, "accept", dwell_ms=500)
            sess.end(submitted=True)
            state_path = tmp / "state" / "S.json"
            sess.checkpoint(state_path)
            with self.assertRaises(session.StateConflict):
                session.Session.resume(state_path)

    def test_state_ahead_of_the_log_is_a_conflict(self):
        with scratch_dir("conflict") as tmp:
            sess = self._midway(tmp)
            state_path = tmp / "state" / "S.json"
            sess.checkpoint(state_path)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["n_events"] = state["n_events"] + 5
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaises(session.StateConflict):
                session.Session.resume(state_path)


if __name__ == "__main__":
    unittest.main()
