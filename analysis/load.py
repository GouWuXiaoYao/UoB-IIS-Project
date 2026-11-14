"""Read ``runs/<run_id>/logs/**/*.jsonl`` into one record per session.

A session is one task under one condition for one participant; its log is the
only data source (AGENTS.md section 2.6). Nothing is inferred from memory or from
the runner's own bookkeeping: if a fact is not in the events, it is reported as
missing rather than guessed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

ENVELOPE = {
    "schema_version", "event_id", "seq", "ts", "session_id", "participant_id",
    "condition", "task_id", "task_index", "pair_id", "phase", "event_type",
    "app_version", "model_id", "model_temperature", "seed",
}


@dataclass
class Session:
    run_id: str
    session_id: str
    participant: str
    condition: str
    task_id: str
    pair_id: str
    path: Path
    n_events: int = 0
    n_bad_lines: int = 0
    ended: bool = False
    completed_all: bool | None = None
    withdrawn: bool | None = None
    tests_pass: bool | None = None
    n_fail: float | None = None
    failing_tests: int | None = None
    debt_delta: float | None = None
    vuln_delta: float | None = None
    lines_added: float | None = None
    lines_removed: float | None = None
    elapsed_ms: float | None = None
    total_elapsed_ms: float | None = None
    gate_latency_ms: float | None = None
    review_dwell_ms: float | None = None
    n_suggestions: int = 0
    n_accepted: int = 0
    blocked_attempts: int = 0
    gate_blocks: int = 0
    explanation_opens: int = 0
    n_toggles: int = 0
    mechanical: bool | None = None
    strata: str | None = None
    app_version: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list, repr=False)

    @property
    def pair_key(self) -> tuple[str, str]:
        return (self.participant, self.task_id)

    def as_row(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "participant": self.participant,
            "session_id": self.session_id,
            "condition": self.condition,
            "pair_id": self.pair_id,
            "task_id": self.task_id,
            "stratum": self.strata or "",
            "ended": self.ended,
            "tests_pass": self.tests_pass,
            "n_fail": self.n_fail,
            "debt_delta": self.debt_delta,
            "vuln_delta": self.vuln_delta,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "elapsed_ms": self.elapsed_ms,
            "gate_latency_ms": self.gate_latency_ms,
            "review_dwell_ms": self.review_dwell_ms,
            "n_suggestions": self.n_suggestions,
            "n_accepted": self.n_accepted,
            "blocked_attempts": self.blocked_attempts,
            "explanation_opens": self.explanation_opens,
            "n_toggles": self.n_toggles,
            "mechanical": self.mechanical,
            "n_events": self.n_events,
        }


def _read_lines(path: Path) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    bad = 0
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(event, dict) and "event_type" in event:
            events.append(event)
        else:
            bad += 1
    return events, bad


def _stamp(session: Session, events: list[dict[str, Any]]) -> None:
    """Fill the envelope fields from the first event that actually carries them.

    ``session_start`` has no task id (it is a session-level event), so reading only
    the first event leaves the task empty and silently collapses every pairing.
    """
    first = events[0]
    session.session_id = str(first.get("session_id") or session.session_id)
    for field in ("participant_id", "condition", "task_id", "pair_id", "app_version"):
        for event in events:
            value = event.get(field)
            if value:
                setattr(
                    session,
                    "participant" if field == "participant_id" else field,
                    str(value),
                )
                break

    toggles: list[float] = []
    for event in events:
        kind = event.get("event_type")
        if kind == "session_end":
            session.ended = True
            session.total_elapsed_ms = event.get("total_elapsed_ms")
            session.completed_all = event.get("completed_all")
            session.withdrawn = event.get("withdrawn")
        elif kind == "task_end":
            session.tests_pass = event.get("tests_pass")
            session.n_fail = event.get("n_fail")
            session.debt_delta = event.get("debt_delta")
            session.vuln_delta = event.get("vuln_delta")
            session.lines_added = event.get("lines_added")
            session.lines_removed = event.get("lines_removed")
            session.elapsed_ms = event.get("elapsed_ms")
        elif kind == "gate_decision":
            blocked = bool(event.get("blocked"))
            session.blocked_attempts += 1 if blocked else 0
            session.gate_blocks += 1 if blocked else 0
            if not blocked and event.get("gate_latency_ms") is not None:
                session.gate_latency_ms = float(event["gate_latency_ms"])
        elif kind == "suggestion_action":
            session.n_suggestions += 1
            if event.get("action") == "accept":
                session.n_accepted += 1
            if event.get("review_dwell_ms") is not None:
                session.review_dwell_ms = float(event["review_dwell_ms"])
        elif kind == "explanation_open":
            session.explanation_opens += 1
        elif kind == "card_item_toggle":
            session.n_toggles += 1
            if event.get("dwell_ms") is not None:
                toggles.append(float(event["dwell_ms"]))

    session.n_events = len(events)
    if session.tests_pass is not None and session.n_fail is not None:
        session.failing_tests = int(session.n_fail)
    if toggles and session.gate_blocks == 0:
        session.mechanical = False


def session_from_file(path: Path, run_id: str) -> Session | None:
    events, bad = _read_lines(path)
    session = Session(
        run_id=run_id,
        session_id=path.stem,
        participant="",
        condition="",
        task_id="",
        pair_id="",
        path=path,
        n_bad_lines=bad,
    )
    if not events:
        return None
    _stamp(session, events)
    session.events = events
    return session


def load_run(run_dir: Path) -> list[Session]:
    run_dir = Path(run_dir)
    logs = run_dir / "logs"
    if not logs.is_dir():
        return []
    out: list[Session] = []
    for path in sorted(logs.rglob("*.jsonl")):
        session = session_from_file(path, run_dir.name)
        if session is not None:
            out.append(session)
    return out


def discover(root: Path) -> list[Path]:
    """Run directories under ``root`` (a run itself, or a directory of runs)."""
    root = Path(root)
    if (root / "logs").is_dir():
        return [root]
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "logs").is_dir())


def read_manifest(run_dir: Path) -> dict[str, Any]:
    path = Path(run_dir) / "manifest.json"
    manifest: dict[str, Any] = {"run_id": Path(run_dir).name}
    if path.is_file():
        try:
            manifest.update(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            manifest["manifest_error"] = "unreadable manifest.json"
    return manifest


def load_runs(root: Path) -> tuple[list[Session], list[dict[str, Any]]]:
    """Load every run under ``root``; also return the manifests that were found.

    ``root`` may itself be a single run directory or a directory of runs. Callers
    that need one run at a time should use :func:`discover` instead: pooling two
    runs would double-count the same cells.
    """
    sessions: list[Session] = []
    manifests: list[dict[str, Any]] = []
    for run in discover(root):
        found = load_run(run)
        if not found:
            continue
        sessions.extend(found)
        manifest = read_manifest(run)
        manifest["_sessions"] = len(found)
        manifests.append(manifest)
    return sessions, manifests


def by_pair(sessions: Iterable[Session], metric: str) -> dict[tuple[str, str], dict[str, float]]:
    """``{(participant, task): {condition: value}}`` for a numeric metric."""
    out: dict[tuple[str, str], dict[str, float]] = {}
    for session in sessions:
        value = getattr(session, metric, None)
        if value is None:
            continue
        out.setdefault(session.pair_key, {})[session.condition] = float(value)
    return out


def paired_series(
    sessions: Iterable[Session], metric: str, baseline: str = "C0", treatment: str = "C1"
) -> tuple[list[str], list[float], list[float], list[str], list[str]]:
    """Return ``labels, baseline_values, treatment_values, participants, tasks``.

    Only keys with both conditions present are kept, so the pairing is explicit
    and the missing-data check can account for what was dropped.
    """
    grouped = by_pair(sessions, metric)
    labels, left, right, participants, tasks = [], [], [], [], []
    for (participant, task), values in sorted(grouped.items()):
        if baseline in values and treatment in values:
            labels.append(f"{task}")
            left.append(values[baseline])
            right.append(values[treatment])
            participants.append(participant)
            tasks.append(task)
    return labels, left, right, participants, tasks
