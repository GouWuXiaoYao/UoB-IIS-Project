"""Acceptance tests for the telemetry logger (SPEC M7 / PLAN milestone M5)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from govern import config, log
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
CONFIG = config.load(ROOT / "config" / "config.json")

META = {
    "session_id": "S-01J9Z7K3",
    "participant_id": "P07",
    "condition": "C1",
    "app_version": "0.3.1+test",
    "model_id": CONFIG.model_id,
    "model_temperature": CONFIG.temperature,
    "seed": CONFIG.seed,
}

TASK = {"task_id": "T-L01a", "task_index": 0, "pair_id": "PAIR-01"}

# One minimal valid payload per event type in SPEC 4.3 (all sixteen of them).
SAMPLES: dict[str, dict] = {
    "session_start": {
        "phase": "setup", "consent_version": "SIM-AUTHOR", "consent_given": True,
        "prior_years": 3.5, "llm_freq": "weekly", "lang_familiarity": 4,
        "schedule_id": "SCHED-A", "device": "win11-chrome",
    },
    "prompt_submit": {
        "phase": "prompt", **TASK, "prompt_id": "P-1", "prompt_len_chars": 42,
        "prompt_sha256": "a" * 64, "attached_files": ["src/app.py"],
    },
    "generation_request": {
        "phase": "generate", **TASK, "suggestion_id": "SUG-1", "request_sha256": "b" * 64,
        "mode": "replay", "latency_ms": 120, "tokens_in": 900, "tokens_out": 300,
    },
    "suggestion_shown": {
        "phase": "review", **TASK, "suggestion_id": "SUG-1", "suggestion_seq": 1,
        "n_files": 3, "n_lines_changed": 24, "n_hunks": 3, "rationale_len_chars": 210,
    },
    "card_shown": {
        "phase": "card", **TASK, "card_id": "CARD-0007", "card_version": "1.0",
        "n_items": 4, "n_required": 4, "latency_from_prompt_ms": 1180,
        "impact_set_hash": "sha256:" + "c" * 16,
    },
    "card_item_toggle": {
        "phase": "card", **TASK, "card_id": "CARD-0007", "item_id": "CI-03",
        "item_category": "cross_module_contract", "checked": True, "dwell_ms": 412,
    },
    "gate_decision": {
        "phase": "gate", **TASK, "card_id": "CARD-0007", "confirmed": True, "blocked": False,
        "n_required": 4, "n_confirmed": 4, "gate_latency_ms": 2600,
    },
    "explanation_open": {
        "phase": "review", **TASK, "suggestion_id": "SUG-1", "layer": "L2", "dwell_ms": 900,
    },
    "suggestion_action": {
        "phase": "review", **TASK, "suggestion_id": "SUG-1", "action": "accept",
        "review_dwell_ms": 2650, "edit_distance_lines": None, "accepted_after_gate": True,
    },
    "suggestion_scored": {
        "phase": "test", **TASK, "suggestion_id": "SUG-1", "is_correct": True,
        "gold_patch_match": False, "scored_by": "hidden_tests", "scorer_version": "rules/1",
    },
    "test_run": {
        "phase": "test", **TASK, "suite": "hidden", "n_pass": 4, "n_fail": 0,
        "failing_tests": [],
    },
    "task_end": {
        "phase": "end", **TASK, "elapsed_ms": 1092512, "submitted": True, "timeout": False,
        "tests_pass": True, "n_fail": 0, "debt_delta": -2.0, "vuln_delta": -1,
        "lines_added": 37, "lines_removed": 29, "n_suggestions": 3, "n_accepted": 2,
        "n_edits": 1, "n_rejects": 0,
    },
    "comprehension_item": {
        "phase": "quiz", **TASK, "quiz_id": "Q-1", "item_id": "QI-1", "answer": "B",
        "correct": True, "response_ms": 4100,
    },
    "survey_response": {
        "phase": "survey", **TASK, "instrument": "NASA_TLX", "item_id": "mental",
        "value": 40.0, "scale_min": 0, "scale_max": 100, "response_ms": 3200,
    },
    "session_end": {
        "phase": "end", "total_elapsed_ms": 2400000, "n_tasks_completed": 2,
        "completed_all": True, "withdrawn": False,
    },
    "integrity_event": {
        "phase": "end", **TASK, "kind": "schema_violation", "detail_len": 12,
        "ref_event_id": None,
    },
}


def _emit(logger: log.Logger, event_type: str) -> dict:
    payload = SAMPLES[event_type]
    logger.emit(event_type, **payload)
    return json.loads(logger.path.read_text(encoding="utf-8").splitlines()[-1])


class EnvelopeTests(unittest.TestCase):
    def test_first_line_has_seq_one_and_a_uuid(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            event_id = logger.emit("prompt_submit", **SAMPLES["prompt_submit"])
            uuid.UUID(event_id)
            row = json.loads(logger.path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["seq"], 1)
            self.assertEqual(row["event_id"], event_id)
            self.assertEqual(row["schema_version"], log.SCHEMA_VERSION)

    def test_seq_increases_by_one(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            logger.emit("card_shown", **SAMPLES["card_shown"])
            logger.emit("card_item_toggle", **SAMPLES["card_item_toggle"])
            rows = [json.loads(line) for line in logger.path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["seq"] for row in rows], [1, 2])

    def test_ts_has_milliseconds_and_an_offset(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            row = _emit(logger, "test_run")
            parsed = datetime.fromisoformat(row["ts"])
            self.assertIsNotNone(parsed.tzinfo)
            self.assertRegex(row["ts"], r"T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}$")

    def test_timestamps_never_go_backwards(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            for _ in range(5):
                _emit(logger, "test_run")
            rows = [json.loads(line) for line in logger.path.read_text(encoding="utf-8").splitlines()]
            stamps = [datetime.fromisoformat(row["ts"]) for row in rows]
            self.assertEqual(stamps, sorted(stamps))

    def test_c2_never_reaches_the_log(self) -> None:
        with scratch_dir() as tmp:
            with self.assertRaises(log.SchemaError):
                log.Logger(tmp, {**META, "condition": "C2"})

    def test_unknown_condition_is_rejected(self) -> None:
        with scratch_dir() as tmp:
            with self.assertRaises(log.SchemaError):
                log.Logger(tmp, {**META, "condition": "X1"})

    def test_log_path_follows_the_spec(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            self.assertEqual(
                logger.path,
                tmp / "logs" / "P07" / "S-01J9Z7K3.jsonl",
            )


class EventTypeTests(unittest.TestCase):
    def test_all_sixteen_event_types_validate(self) -> None:
        self.assertEqual(len(log.EVENT_FIELDS), 16)
        self.assertEqual(set(log.EVENT_FIELDS), set(SAMPLES))
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            for event_type in log.EVENT_FIELDS:
                with self.subTest(event_type=event_type):
                    row = _emit(logger, event_type)
                    self.assertEqual(log.validate(row), [])

    def test_unknown_event_type_is_rejected(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            with self.assertRaises(log.SchemaError):
                logger.emit("telepathy", phase="setup")

    def test_missing_private_field_is_rejected(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            payload = dict(SAMPLES["gate_decision"])
            del payload["n_confirmed"]
            with self.assertRaises(log.SchemaError):
                logger.emit("gate_decision", **payload)

    def test_wrong_type_is_rejected(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            payload = {**SAMPLES["test_run"], "n_pass": "4"}
            with self.assertRaises(log.SchemaError):
                logger.emit("test_run", **payload)

    def test_bool_is_not_accepted_where_an_integer_is_expected(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            payload = {**SAMPLES["test_run"], "n_fail": True}
            with self.assertRaises(log.SchemaError):
                logger.emit("test_run", **payload)

    def test_null_allowed_field_accepts_none(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            row = _emit(logger, "suggestion_action")
            self.assertIsNone(row["edit_distance_lines"])

    def test_empty_string_is_not_a_stand_in_for_null(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            payload = {**SAMPLES["suggestion_action"], "edit_distance_lines": ""}
            with self.assertRaises(log.SchemaError):
                logger.emit("suggestion_action", **payload)

    def test_unknown_field_is_rejected_unless_prefixed(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            with self.assertRaises(log.SchemaError):
                logger.emit("test_run", **{**SAMPLES["test_run"], "mystery": 1})
            logger.emit("test_run", **{**SAMPLES["test_run"], "x_future": "ok"})

    def test_invalid_enum_value_is_rejected(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            with self.assertRaises(log.SchemaError):
                logger.emit("suggestion_action", **{**SAMPLES["suggestion_action"], "action": "ponder"})


class BodyFieldTests(unittest.TestCase):
    """SPEC M7 acceptance 6 / Q7: no prose ever reaches the log."""

    def test_body_fields_are_refused(self) -> None:
        for field in ("text", "content", "body", "prompt_raw", "diff", "patch"):
            with self.subTest(field=field), scratch_dir() as tmp:
                logger = log.Logger(tmp, META)
                with self.assertRaises(log.SchemaError):
                    logger.emit("prompt_submit", **{**SAMPLES["prompt_submit"], field: "secret prose"})

    def test_body_field_suffixes_are_refused_too(self) -> None:
        for field in ("prompt_text", "file_content", "response_body", "diff_raw"):
            with self.subTest(field=field), scratch_dir() as tmp:
                logger = log.Logger(tmp, META)
                with self.assertRaises(log.SchemaError):
                    logger.emit("prompt_submit", **{**SAMPLES["prompt_submit"], field: "x"})

    def test_hash_and_length_are_the_accepted_alternative(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            row = _emit(logger, "prompt_submit")
            self.assertEqual(row["prompt_len_chars"], 42)
            self.assertEqual(row["prompt_sha256"], "a" * 64)

    def test_nothing_written_when_a_body_field_is_refused(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            logger.emit("test_run", **SAMPLES["test_run"])
            before = logger.path.read_text(encoding="utf-8")
            with self.assertRaises(log.SchemaError):
                logger.emit("test_run", **{**SAMPLES["test_run"], "text": "leak"})
            self.assertEqual(logger.path.read_text(encoding="utf-8"), before)


class PiiTests(unittest.TestCase):
    def test_participant_id_must_be_a_pseudonym(self) -> None:
        for bad in ("alice@example.com", "1234567", "student_1234567", "Ann Smith"):
            with self.subTest(participant=bad), scratch_dir() as tmp:
                with self.assertRaises(log.SchemaError):
                    log.Logger(tmp, {**META, "participant_id": bad})

    def test_pseudonyms_are_accepted(self) -> None:
        for good in ("P07", "AUTH", "SIM-AUTHOR"):
            with self.subTest(participant=good), scratch_dir() as tmp:
                log.Logger(tmp, {**META, "participant_id": good})


class SizeTests(unittest.TestCase):
    def test_oversized_line_is_refused(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            with self.assertRaises(log.SchemaError):
                logger.emit("test_run", **{**SAMPLES["test_run"], "failing_tests": ["x" * 5000]})

    def test_long_arrays_are_truncated_with_a_running_total(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            names = [f"test_{i}" for i in range(30)]
            row = _emit_failing(logger, names)
            self.assertEqual(len(row["failing_tests"]), 20)
            self.assertEqual(row["x_failing_tests_total"], 30)


def _emit_failing(logger: log.Logger, names: list[str]) -> dict:
    logger.emit("test_run", **{**SAMPLES["test_run"], "n_fail": len(names), "failing_tests": names})
    return json.loads(logger.path.read_text(encoding="utf-8").splitlines()[-1])


class AtomicityTests(unittest.TestCase):
    """SPEC M7 acceptance 4: never half a JSON object."""

    def test_a_torn_last_line_is_repaired_on_reopen(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            logger.emit("test_run", **SAMPLES["test_run"])
            logger.emit("test_run", **SAMPLES["test_run"])
            raw = logger.path.read_bytes()
            torn = raw[: len(raw) - 12]  # cut into the middle of the second object
            logger.path.write_bytes(torn)

            reopened = log.Logger(tmp, META)
            self.assertNotEqual(reopened.path.read_bytes(), torn)
            for line in reopened.path.read_text(encoding="utf-8").splitlines():
                json.loads(line)
            self.assertEqual(reopened.emit("test_run", **SAMPLES["test_run"]) is not None, True)

    def test_seq_continues_from_the_last_complete_line(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            logger.emit("test_run", **SAMPLES["test_run"])
            logger.emit("test_run", **SAMPLES["test_run"])
            raw = logger.path.read_bytes()
            logger.path.write_bytes(raw[: len(raw) - 12])

            reopened = log.Logger(tmp, META)
            row = _emit(reopened, "test_run")
            # The torn event is gone, so its seq is reused: no gap, no duplicate.
            self.assertEqual(row["seq"], 2)
            seqs = [json.loads(line)["seq"] for line in reopened.path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(seqs, [1, 2])

    def test_no_tmp_file_is_left_behind(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            logger.emit("test_run", **SAMPLES["test_run"])
            leftovers = list(logger.path.parent.glob("*.tmp"))
            self.assertEqual(leftovers, [])


class PurgeTests(unittest.TestCase):
    def test_purge_removes_old_sessions_and_keeps_recent_ones(self) -> None:
        with scratch_dir() as tmp:
            old = log.Logger(tmp, {**META, "session_id": "S-OLD"})
            old.emit("test_run", **SAMPLES["test_run"])
            new = log.Logger(tmp, {**META, "session_id": "S-NEW"})
            new.emit("test_run", **SAMPLES["test_run"])

            long_ago = (datetime.now(timezone.utc) - timedelta(days=200)).timestamp()
            os.utime(old.path, (long_ago, long_ago))

            removed = log.purge(tmp, date.today())
            self.assertEqual(removed, [str(old.path)])
            self.assertFalse(old.path.exists())
            self.assertTrue(new.path.exists())

    def test_purge_leaves_no_jsonl_or_tmp_behind(self) -> None:
        with scratch_dir() as tmp:
            old = log.Logger(tmp, {**META, "session_id": "S-OLD"})
            old.emit("test_run", **SAMPLES["test_run"])
            (old.path.parent / "S-OLD.jsonl.tmp").write_text("{}", encoding="utf-8")
            long_ago = (datetime.now(timezone.utc) - timedelta(days=200)).timestamp()
            os.utime(old.path, (long_ago, long_ago))

            log.purge(tmp, date.today())
            self.assertEqual(list((tmp / "logs").rglob("*.jsonl*")), [])

    def test_purge_reports_what_it_removed(self) -> None:
        with scratch_dir() as tmp:
            old = log.Logger(tmp, {**META, "session_id": "S-OLD"})
            old.emit("test_run", **SAMPLES["test_run"])
            long_ago = (datetime.now(timezone.utc) - timedelta(days=200)).timestamp()
            os.utime(old.path, (long_ago, long_ago))
            self.assertEqual(len(log.purge(tmp, date.today())), 1)


class PiiScanTests(unittest.TestCase):
    def test_a_real_log_scans_clean(self) -> None:
        with scratch_dir() as tmp:
            logger = log.Logger(tmp, META)
            for event_type in log.EVENT_FIELDS:
                logger.emit(event_type, **SAMPLES[event_type])
            self.assertEqual(log.scan_pii(logger.path), [])

    def test_identifiers_are_found_in_a_synthetic_file(self) -> None:
        with scratch_dir() as tmp:
            path = tmp / "bad.jsonl"
            path.write_text(
                json.dumps({"participant_id": "alice@example.com"}) + "\n"
                + json.dumps({"schedule_id": "s1234567"}) + "\n"
                + json.dumps({"device": "Ann Smith"}) + "\n",
                encoding="utf-8",
            )
            findings = log.scan_pii(path)
            self.assertGreaterEqual(len(findings), 3)
            self.assertTrue(any("participant_id" in finding for finding in findings))

    def test_scan_catches_a_nested_value(self) -> None:
        with scratch_dir() as tmp:
            path = tmp / "nested.jsonl"
            path.write_text(json.dumps({"failing_tests": ["ok", "bob@uni.ac.uk"]}) + "\n", encoding="utf-8")
            self.assertTrue(log.scan_pii(path))


class CliTests(unittest.TestCase):
    def test_selftest_names_the_coverage(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "govern.log", "--selftest"],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("16 event types", proc.stdout)
        self.assertIn("body field refused", proc.stdout)
        self.assertIn("purge clean", proc.stdout)


if __name__ == "__main__":
    unittest.main()
