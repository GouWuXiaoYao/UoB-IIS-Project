"""Turn session logs into the numbers the study is about.

Every figure here is recomputed from the JSONL on disk — `metrics.json` is a
cache, never a source. That is SPEC 4.5's "日志是唯一数据源" taken literally: if
a number cannot be rebuilt from `logs/`, it does not belong in the file.

The two thresholds used below (`tau_review_ms`, `mech_dwell_ms`) come from
`config/config.json`, which is also what a re-analysis would read; they are the
only place where "blind accept" and "mechanical confirmation" are defined.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Iterable

from govern import config as config_mod

METRIC_VERSION = "metrics/1.0.0"


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------
def read_session(log_path: str | Path) -> dict[str, Any] | None:
    """Load one session log; ``None`` when the file has no usable events."""
    path = Path(log_path)
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a torn tail line is not a session
    except OSError:
        return None
    if not events:
        return None
    first = events[0]
    return {
        "session_id": first.get("session_id", path.stem),
        "participant": first.get("participant_id", ""),
        "condition": first.get("condition", ""),
        "task_id": first.get("task_id", ""),
        "pair_id": first.get("pair_id", ""),
        "events": events,
        "path": str(path),
    }


def collect(logs_root: str | Path) -> list[dict[str, Any]]:
    root = Path(logs_root)
    if not root.is_dir():
        return []
    sessions = []
    for path in sorted(root.rglob("*.jsonl")):
        session = read_session(path)
        if session is not None:
            sessions.append(session)
    return sessions


def _of(session: dict[str, Any], event_type: str) -> list[dict[str, Any]]:
    return [event for event in session["events"] if event.get("event_type") == event_type]


# ---------------------------------------------------------------------------
# per-session facts
# ---------------------------------------------------------------------------
def escapes(session: dict[str, Any]) -> bool:
    """A task ended with a failing hidden suite — SPEC 5.2's "逃逸缺陷"."""
    ends = _of(session, "task_end")
    return bool(ends) and ends[-1].get("tests_pass") is False


def blind_accepts(session: dict[str, Any], tau_review_ms: int) -> int:
    """Accepts that were fast and had no explanation opened (SPEC 5.2)."""
    opened = {event.get("suggestion_id") for event in _of(session, "explanation_open")}
    count = 0
    for event in _of(session, "suggestion_action"):
        if event.get("action") != "accept":
            continue
        if not event.get("accepted_after_gate"):
            continue
        if int(event.get("review_dwell_ms") or 0) >= tau_review_ms:
            continue
        if event.get("suggestion_id") in opened:
            continue
        count += 1
    return count


def confirmations(session: dict[str, Any], mech_dwell_ms: int) -> tuple[int, int]:
    """``(confirmations, mechanical)`` for one session.

    A confirmation is mechanical when the median toggle dwell before it is below
    the threshold and nothing was un-ticked (SPEC 5.2, A-6).
    """
    total = 0
    mechanical = 0
    dwells: list[int] = []
    for event in session["events"]:
        kind = event.get("event_type")
        if kind == "card_item_toggle":
            dwells.append(int(event.get("dwell_ms") or 0))
            continue
        if kind != "gate_decision":
            continue
        if not event.get("confirmed"):
            continue
        total += 1
        if event.get("n_confirmed") == event.get("n_required") and dwells:
            if statistics.median(dwells) < mech_dwell_ms:
                mechanical += 1
        dwells = []
    return total, mechanical


def debt_delta(session: dict[str, Any]) -> float | None:
    ends = _of(session, "task_end")
    if not ends:
        return None
    value = ends[-1].get("debt_delta")
    return None if value is None else float(value)


def elapsed_ms(session: dict[str, Any]) -> int | None:
    ends = _of(session, "task_end")
    if not ends:
        return None
    value = ends[-1].get("elapsed_ms")
    return None if value is None else int(value)


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------
def _mean(values: Iterable[float]) -> float | None:
    items = [value for value in values if value is not None]
    if not items:
        return None
    return round(sum(items) / len(items), 4)


def _condition_block(sessions: list[dict[str, Any]], tau_review_ms: int, mech_dwell_ms: int) -> dict[str, Any]:
    n = len(sessions)
    escaped = sum(1 for session in sessions if escapes(session))
    actions = sum(len(_of(session, "suggestion_action")) for session in sessions)
    accepts = sum(1 for session in sessions for event in _of(session, "suggestion_action") if event.get("action") == "accept")
    edits = sum(1 for session in sessions for event in _of(session, "suggestion_action") if event.get("action") == "edit")
    rejects = sum(1 for session in sessions for event in _of(session, "suggestion_action") if event.get("action") == "reject")
    blind = sum(blind_accepts(session, tau_review_ms) for session in sessions)
    confirmations_total = 0
    mechanical_total = 0
    for session in sessions:
        total, mechanical = confirmations(session, mech_dwell_ms)
        confirmations_total += total
        mechanical_total += mechanical
    blocked = sum(
        1
        for session in sessions
        for event in _of(session, "gate_decision")
        if event.get("blocked")
    )
    toggles = sum(len(_of(session, "card_item_toggle")) for session in sessions)
    return {
        "n_sessions": n,
        "n_completed": sum(1 for session in sessions if _of(session, "session_end") and _of(session, "session_end")[-1].get("completed_all")),
        "escapes": escaped,
        "escape_defect_rate": round(escaped / n, 4) if n else None,
        "mean_debt_delta": _mean(debt_delta(session) for session in sessions),
        "mean_elapsed_ms": _mean(elapsed_ms(session) for session in sessions),
        "n_card_toggles": toggles,
        "mean_card_toggles": round(toggles / n, 4) if n else None,
        "blocked_attempts": blocked,
        "confirmations": confirmations_total,
        "mechanical_confirmations": mechanical_total,
        "mechanical_share": round(mechanical_total / confirmations_total, 4) if confirmations_total else None,
        "n_actions": actions,
        "accepts": accepts,
        "edits": edits,
        "rejects": rejects,
        "blind_accepts": blind,
        "oti": round(blind / actions, 4) if actions else None,
    }


def summarise(sessions: list[dict[str, Any]], tau_review_ms: int, mech_dwell_ms: int) -> dict[str, Any]:
    by_condition: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        by_condition.setdefault(session["condition"], []).append(session)

    pairs: dict[str, dict[str, Any]] = {}
    for session in sessions:
        pair = session.get("pair_id") or "UNKNOWN"
        entry = pairs.setdefault(pair, {"pair_id": pair})
        bucket = entry.setdefault(session["condition"], [])
        bucket.append(session)

    pair_rows = []
    for pair_id in sorted(pairs):
        entry = pairs[pair_id]
        row: dict[str, Any] = {"pair_id": pair_id}
        for condition in sorted(by_condition):
            row[condition] = _condition_block(entry.get(condition, []), tau_review_ms, mech_dwell_ms)
        pair_rows.append(row)

    return {
        "metric_version": METRIC_VERSION,
        "tau_review_ms": tau_review_ms,
        "mech_dwell_ms": mech_dwell_ms,
        "totals": {
            "n_sessions": len(sessions),
            "n_conditions": len(by_condition),
            "n_pairs": len(pair_rows),
        },
        "conditions": {
            condition: _condition_block(by_condition[condition], tau_review_ms, mech_dwell_ms)
            for condition in sorted(by_condition)
        },
        "pairs": pair_rows,
    }


def thresholds(config_path: str | Path | None = None) -> tuple[int, int]:
    cfg = config_mod.load() if config_path is None else config_mod.load(config_path)
    return cfg.tau_review_ms, cfg.mech_dwell_ms


def rebuild(run_dir: str | Path) -> dict[str, Any]:
    """Recompute the metrics of a finished run from its logs."""
    run = Path(run_dir)
    tau_review_ms, mech_dwell_ms = thresholds()
    return summarise(collect(run / "logs"), tau_review_ms, mech_dwell_ms)


def write(run_dir: str | Path, data: dict[str, Any]) -> Path:
    path = Path(run_dir) / "metrics.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
