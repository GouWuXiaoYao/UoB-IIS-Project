"""Telemetry logger (SPEC M7 / PLAN milestone M5).

Every metric in the specification is recomputed from these files, so this module
is deliberately strict: an event that does not match the schema is **refused**
(never written half, never silently dropped), prose is refused outright (only
``sha256`` plus a length), and a torn trailing line left by a killed process is
repaired on the next open rather than being read back as data.

Layout: ``<run_dir>/logs/<participant_id>/<session_id>.jsonl``, one JSON object
per line, append-only.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field as dc_field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from govern import config

SCHEMA_VERSION = "1.0.0"
# Format constants, not tunable parameters: SPEC M7 acceptance 5 fixes them at
# 4 KB per line and 20 array items. Changing either changes the meaning of the
# schema, so they live here next to SCHEMA_VERSION rather than in config/.
MAX_LINE_BYTES = 4096
MAX_ARRAY_ITEMS = 20

PHASES = (
    "setup",
    "prompt",
    "card",
    "gate",
    "generate",
    "review",
    "test",
    "quiz",
    "survey",
    "end",
)

# Field kinds: str / int / num / bool / arr (array of strings) / enum.
STR = "str"
INT = "int"
NUM = "num"
BOOL = "bool"
ARR = "arr"
ENUM = "enum"

# Names that would put prose (or the answer) into the log. Q7: hashes only.
BODY_FIELD_NAMES = frozenset({"text", "content", "body", "prompt_raw", "diff", "patch"})
BODY_FIELD_SUFFIXES = ("_text", "_content", "_body", "_raw", "_diff", "_patch")


@dataclass(frozen=True)
class Field:
    kind: str
    nullable: bool = False
    choices: tuple[str, ...] = ()


def _f(kind: str, nullable: bool = False) -> Field:
    return Field(kind, nullable)


def _e(*choices: str, nullable: bool = False) -> Field:
    return Field(ENUM, nullable, tuple(choices))


ENVELOPE: dict[str, Field] = {
    "schema_version": _f(STR),
    "event_id": _f(STR),
    "seq": _f(INT),
    "ts": _f(STR),
    "session_id": _f(STR),
    "participant_id": _f(STR),
    "condition": _e("C0", "C1"),
    "task_id": _f(STR, nullable=True),
    "task_index": _f(INT, nullable=True),
    "pair_id": _f(STR, nullable=True),
    "phase": _e(*PHASES),
    "event_type": _f(STR),
    "app_version": _f(STR),
    "model_id": _f(STR, nullable=True),
    "model_temperature": _f(NUM, nullable=True),
    "seed": _f(INT, nullable=True),
}

CATEGORIES = ("global_var", "cross_module_contract", "side_effect", "test_impact", "other")

EVENT_FIELDS: dict[str, dict[str, Field]] = {
    "session_start": {
        "consent_version": _f(STR),
        "consent_given": _f(BOOL),
        "prior_years": _f(NUM),
        "llm_freq": _e("never", "monthly", "weekly", "daily"),
        "lang_familiarity": _f(INT),
        "schedule_id": _f(STR),
        "device": _f(STR),
    },
    "prompt_submit": {
        "prompt_id": _f(STR),
        "prompt_len_chars": _f(INT),
        "prompt_sha256": _f(STR),
        "attached_files": _f(ARR),
    },
    "generation_request": {
        "suggestion_id": _f(STR, nullable=True),
        "request_sha256": _f(STR),
        "mode": _e("mock", "live", "replay"),
        "latency_ms": _f(INT),
        "tokens_in": _f(INT, nullable=True),
        "tokens_out": _f(INT, nullable=True),
    },
    "suggestion_shown": {
        "suggestion_id": _f(STR),
        "suggestion_seq": _f(INT),
        "n_files": _f(INT),
        "n_lines_changed": _f(INT),
        "n_hunks": _f(INT),
        "rationale_len_chars": _f(INT),
    },
    "card_shown": {
        "card_id": _f(STR),
        "card_version": _f(STR),
        "n_items": _f(INT),
        "n_required": _f(INT),
        "latency_from_prompt_ms": _f(INT),
        "impact_set_hash": _f(STR),
    },
    "card_item_toggle": {
        "card_id": _f(STR),
        "item_id": _f(STR),
        "item_category": _e(*CATEGORIES),
        "checked": _f(BOOL),
        "dwell_ms": _f(INT),
    },
    "gate_decision": {
        "card_id": _f(STR),
        "confirmed": _f(BOOL),
        "blocked": _f(BOOL),
        "n_required": _f(INT),
        "n_confirmed": _f(INT),
        "gate_latency_ms": _f(INT),
    },
    "explanation_open": {
        "suggestion_id": _f(STR),
        "layer": _e("L1", "L2"),
        "dwell_ms": _f(INT),
    },
    "suggestion_action": {
        "suggestion_id": _f(STR),
        "action": _e("accept", "edit", "reject", "regenerate"),
        "review_dwell_ms": _f(INT),
        "edit_distance_lines": _f(INT, nullable=True),
        "accepted_after_gate": _f(BOOL),
    },
    "suggestion_scored": {
        "suggestion_id": _f(STR),
        "is_correct": _f(BOOL, nullable=True),
        "gold_patch_match": _f(BOOL),
        "scored_by": _e("hidden_tests", "gold_diff", "manual"),
        "scorer_version": _f(STR),
    },
    "test_run": {
        "task_id": _f(STR),
        "suite": _e("visible", "hidden"),
        "n_pass": _f(INT),
        "n_fail": _f(INT),
        "failing_tests": _f(ARR),
    },
    "task_end": {
        "elapsed_ms": _f(INT),
        "submitted": _f(BOOL),
        "timeout": _f(BOOL),
        "tests_pass": _f(BOOL),
        "n_fail": _f(INT),
        "debt_delta": _f(NUM),
        "vuln_delta": _f(INT),
        "lines_added": _f(INT),
        "lines_removed": _f(INT),
        "n_suggestions": _f(INT),
        "n_accepted": _f(INT),
        "n_edits": _f(INT),
        "n_rejects": _f(INT),
    },
    "comprehension_item": {
        "quiz_id": _f(STR),
        "item_id": _f(STR),
        "answer": _f(STR),
        "correct": _f(BOOL),
        "response_ms": _f(INT),
    },
    "survey_response": {
        "instrument": _e("NASA_TLX", "SUS", "custom"),
        "item_id": _f(STR),
        "value": _f(NUM),
        "scale_min": _f(NUM),
        "scale_max": _f(NUM),
        "response_ms": _f(INT),
    },
    "session_end": {
        "total_elapsed_ms": _f(INT),
        "n_tasks_completed": _f(INT),
        "completed_all": _f(BOOL),
        "withdrawn": _f(BOOL),
    },
    "integrity_event": {
        "kind": _e("mock_mismatch", "schema_violation", "crash_recovered", "timeout_kill"),
        "detail_len": _f(INT),
        "ref_event_id": _f(STR, nullable=True),
    },
}

PSEUDONYM = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
DIGIT_RUN = re.compile(r"\d{6,}")
HAS_EMAIL_OR_SPACE = re.compile(r"[\s@.]")


class SchemaError(ValueError):
    """Raised instead of writing an event that does not match the schema."""


def _is_body_field(name: str) -> bool:
    return name in BODY_FIELD_NAMES or name.endswith(BODY_FIELD_SUFFIXES)


def _check_value(name: str, value: object, spec: Field) -> list[str]:
    errors: list[str] = []
    if value is None:
        if not spec.nullable:
            errors.append(f"{name}: null is not allowed")
        return errors
    if isinstance(value, str) and value == "":
        errors.append(f"{name}: empty string is not a stand-in for null")
        return errors
    if spec.kind == BOOL:
        if not isinstance(value, bool):
            errors.append(f"{name}: expected boolean, got {type(value).__name__}")
    elif spec.kind == INT:
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{name}: expected integer, got {type(value).__name__}")
    elif spec.kind == NUM:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{name}: expected number, got {type(value).__name__}")
    elif spec.kind == STR:
        if not isinstance(value, str):
            errors.append(f"{name}: expected string, got {type(value).__name__}")
    elif spec.kind == ARR:
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{name}: expected an array of strings")
    elif spec.kind == ENUM:
        if not isinstance(value, str):
            errors.append(f"{name}: expected string, got {type(value).__name__}")
        elif value not in spec.choices:
            errors.append(f"{name}: {value!r} is not one of {list(spec.choices)}")
    return errors


def validate(ev: dict) -> list[str]:
    """Return a list of schema problems; an empty list means the event is valid."""
    errors: list[str] = []

    for name in ev:
        if name.startswith("x_"):
            continue
        if _is_body_field(name):
            errors.append(f"{name}: body/prose fields are not allowed (Q7: hash + length only)")
        elif name not in ENVELOPE and name not in EVENT_FIELDS.get(str(ev.get("event_type")), {}):
            errors.append(f"{name}: unknown field")

    for name, spec in ENVELOPE.items():
        if name not in ev:
            errors.append(f"{name}: missing")
            continue
        errors.extend(_check_value(name, ev[name], spec))

    event_type = ev.get("event_type")
    if isinstance(event_type, str) and event_type not in EVENT_FIELDS:
        errors.append(f"event_type: {event_type!r} is not a known event type")
        return errors
    if event_type == "session_start":
        return errors

    for name, spec in EVENT_FIELDS.get(str(event_type), {}).items():
        if name not in ev:
            errors.append(f"{name}: missing for {event_type}")
            continue
        errors.extend(_check_value(name, ev[name], spec))

    if ev.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION!r}")
    if _check_str(ev.get("event_id")):
        try:
            uuid.UUID(str(ev["event_id"]))
        except ValueError:
            errors.append("event_id: not a UUID")
    pair = (ev.get("task_id"), ev.get("task_index"))
    if pair[0] is None and pair[1] is not None:
        errors.append("task_index: must be null when task_id is null")
    return errors


def _check_str(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(previous: datetime | None) -> tuple[str, datetime]:
    now = _now()
    current = now.replace(microsecond=(now.microsecond // 1000) * 1000)
    if previous is not None and current <= previous:
        current = previous + timedelta(milliseconds=1)
    return current.isoformat(timespec="milliseconds"), current


class Logger:
    """Append-only JSONL writer for one session."""

    def __init__(self, run_dir: Path, session_meta: dict) -> None:
        self.run_dir = Path(run_dir)
        meta = dict(session_meta)
        self.session_id = str(meta["session_id"])
        self.participant_id = str(meta["participant_id"])

        cfg = config.load()
        condition = str(meta["condition"])
        if condition not in cfg.conditions:
            raise SchemaError(f"condition: {condition!r} is not in {list(cfg.conditions)}")
        if not _valid_pseudonym(self.participant_id):
            raise SchemaError(
                f"participant_id: {self.participant_id!r} is not a pseudonym "
                "(no spaces, emails, or long digit runs)"
            )
        if not isinstance(meta.get("app_version"), str):
            raise SchemaError("app_version: missing from session_meta")

        self._meta = {
            "session_id": self.session_id,
            "participant_id": self.participant_id,
            "condition": condition,
            "app_version": meta["app_version"],
            "model_id": meta.get("model_id"),
            "model_temperature": meta.get("model_temperature"),
            "seed": meta.get("seed"),
        }
        self.path = self.run_dir / "logs" / self.participant_id / f"{self.session_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = self._repair_and_count()
        self._last_ts: datetime | None = self._last_stamp()

    # -- file state ------------------------------------------------------
    def _repair_and_count(self) -> int:
        if not self.path.exists():
            return 1
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            cut = raw.rfind(b"\n") + 1
            self.path.write_bytes(raw[:cut])
            raw = raw[:cut]
        last = 0
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            last = int(json.loads(line)["seq"])
        return last + 1

    def _last_stamp(self) -> datetime | None:
        if not self.path.exists():
            return None
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return None
        return datetime.fromisoformat(json.loads(lines[-1])["ts"])

    # -- writing ---------------------------------------------------------
    def emit(self, event_type: str, **fields) -> str:
        if event_type not in EVENT_FIELDS:
            raise SchemaError(f"event_type: {event_type!r} is not a known event type")

        payload = dict(fields)
        for name, value in list(payload.items()):
            if isinstance(value, list) and len(value) > MAX_ARRAY_ITEMS:
                payload[f"x_{name}_total"] = len(value)
                payload[name] = value[:MAX_ARRAY_ITEMS]

        ts, stamp = _stamp(self._last_ts)
        event = {
            "schema_version": SCHEMA_VERSION,
            "event_id": str(uuid.uuid4()),
            "seq": self._seq,
            "ts": ts,
            "phase": payload.pop("phase", None),
            "event_type": event_type,
            **self._meta,
            "task_id": payload.pop("task_id", None),
            "task_index": payload.pop("task_index", None),
            "pair_id": payload.pop("pair_id", None),
            **payload,
        }

        errors = validate(event)
        if errors:
            raise SchemaError("; ".join(errors))

        line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        encoded = line.encode("utf-8")
        if len(encoded) > MAX_LINE_BYTES:
            raise SchemaError(f"line too long: {len(encoded)} bytes (limit {MAX_LINE_BYTES})")

        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_BINARY)
        try:
            os.write(fd, encoded)
            os.fsync(fd)
        finally:
            os.close(fd)

        self._seq += 1
        self._last_ts = stamp
        return event["event_id"]


def _valid_pseudonym(value: str) -> bool:
    if HAS_EMAIL_OR_SPACE.search(value):
        return False
    if DIGIT_RUN.search(value):
        return False
    return bool(PSEUDONYM.match(value))


UUID_SHAPE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
HEX_BLOB = re.compile(r"\b[0-9a-fA-F]{32,}\b")

PII_PATTERNS = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "e-mail address"),
    (re.compile(r"(?<![0-9A-Fa-f-])\d{6,}(?![0-9A-Fa-f-])"), "student-number-shaped digit run"),
    (re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+[A-Z][a-z]+"), "titled name"),
    (re.compile(r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b"), "two capitalised words (possible name)"),
)


def scan_pii(path: Path) -> list[str]:
    """Scan a log file for identifying strings (SPEC M7 acceptance 3).

    Returns one finding per offending string value. Every string in every line
    is scanned, so an identifier that slipped in through a field this module
    does not own is still caught. Event ids and hashes are stripped first: they
    are opaque hex, and a hex blob can contain a six-digit run by chance.
    """
    findings: list[str] = []
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        for key, value in _walk_strings(json.loads(line)):
            subject = HEX_BLOB.sub("", UUID_SHAPE.sub("", value))
            for pattern, label in PII_PATTERNS:
                if pattern.search(subject):
                    findings.append(f"line {lineno}: {key} looks like a {label}: {value!r}")
    return findings


def _walk_strings(node: object, prefix: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, str):
        found.append((prefix or "<value>", node))
    elif isinstance(node, dict):
        for key, value in node.items():
            found.extend(_walk_strings(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_walk_strings(value, f"{prefix}[{index}]"))
    return found


def purge(run_dir: Path, before: date) -> list[str]:
    """Delete session logs last modified before ``before``; return what went.

    ``*.jsonl.tmp`` files are always removed: they only ever exist between a
    crash and the next open, so leaving them behind would mean "purged" is a
    claim the directory does not support.
    """
    root = Path(run_dir) / "logs"
    removed: list[str] = []
    if not root.exists():
        return removed
    cutoff = datetime.combine(before, datetime.min.time(), tzinfo=timezone.utc).timestamp()
    for path in sorted(root.rglob("*.jsonl.tmp")):
        if path.is_file():
            removed.append(str(path))
            path.unlink()
    for path in sorted(root.rglob("*.jsonl")):
        if path.is_file() and path.stat().st_mtime < cutoff:
            removed.append(str(path))
            path.unlink()
    return removed


def _selftest() -> int:
    import tempfile  # noqa: PLC0415

    root = Path(".scratch") / f"log-selftest-{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    failures = 0

    meta = {
        "session_id": "S-SELFTEST",
        "participant_id": "AUTH",
        "condition": "C1",
        "app_version": "selftest",
        "model_id": "replay-selftest",
        "model_temperature": 0.0,
        "seed": 0,
    }
    logger = Logger(root, meta)
    base = {"phase": "test", "task_id": "T-L01a", "task_index": 0, "pair_id": "PAIR-01"}
    samples = {
        "test_run": {**base, "suite": "hidden", "n_pass": 1, "n_fail": 0, "failing_tests": []},
        "gate_decision": {
            **base, "phase": "gate", "card_id": "CARD-1", "confirmed": False,
            "blocked": True, "n_required": 3, "n_confirmed": 0, "gate_latency_ms": 10,
        },
    }
    for event_type, payload in samples.items():
        event_id = logger.emit(event_type, **payload)
        row = json.loads(logger.path.read_text(encoding="utf-8").splitlines()[-1])
        if row["event_id"] != event_id or validate(row):
            print(f"FAIL: {event_type} did not round-trip")
            failures += 1

    try:
        logger.emit("test_run", **{**samples["test_run"], "text": "prose"})
    except SchemaError:
        print("  body field refused: no prose is ever written")
    else:
        print("FAIL: a body field was accepted")
        failures += 1

    long_ago = (datetime.now(timezone.utc) - timedelta(days=400)).timestamp()
    os.utime(logger.path, (long_ago, long_ago))
    removed = purge(root, date.today())
    residue = list(root.rglob("*.jsonl*")) if root.exists() else []
    if residue:
        print(f"FAIL: purge left {residue}")
        failures += 1
    else:
        print(f"  purge clean: removed {len(removed)} file(s), no .jsonl or .tmp left")

    status = "ok" if not failures else "FAIL"
    print(f"{status}: {len(EVENT_FIELDS)} event types, seq from 1, atomic append, purge clean")
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(prog="python -m govern.log")
    parser.add_argument("--selftest", action="store_true", help="validate the schema and purge")
    parser.add_argument("--purge", action="store_true", help="delete logs older than --before")
    parser.add_argument("--before", default=None, help="ISO date, e.g. 2026-01-01")
    parser.add_argument("--run-dir", default="runs", help="run directory to purge")
    parser.add_argument("--validate", default=None, help="validate an existing .jsonl file")
    parser.add_argument("--scan", default=None, help="scan a .jsonl file for identifying strings")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.purge:
        if not args.before:
            parser.error("--purge needs --before YYYY-MM-DD")
        removed = purge(Path(args.run_dir), date.fromisoformat(args.before))
        for path in removed:
            print(f"removed {path}")
        print(f"ok: {len(removed)} file(s) removed before {args.before}")
        return 0
    if args.validate:
        bad = 0
        for lineno, line in enumerate(Path(args.validate).read_text(encoding="utf-8").splitlines(), 1):
            problems = validate(json.loads(line))
            if problems:
                bad += 1
                print(f"line {lineno}: {'; '.join(problems)}")
        print(f"{'ok' if not bad else 'FAIL'}: {lineno} line(s) checked, {bad} invalid")
        return 0 if not bad else 1
    if args.scan:
        findings = scan_pii(Path(args.scan))
        for finding in findings:
            print(finding)
        print(f"{'ok' if not findings else 'FAIL'}: {len(findings)} identifying string(s)")
        return 0 if not findings else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
