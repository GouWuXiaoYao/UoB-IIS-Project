"""Execute a plan: one session per cell, bounded concurrency, resumable.

Three properties matter more than speed here:

* **Isolation** — one failing cell is recorded and the batch continues. A failed
  cell must never look like a successful one, so its record says which cell, which
  task and what the exception was.
* **Resumability** — a cell is done when its log ends with ``session_end``. Nothing
  else is trusted, so a crash mid-session leaves the cell to be re-run rather than
  counted as complete (SPEC M2 acceptance 4: state is rebuildable from logs).
* **Provenance** — before the first session starts, the run directory receives a
  config snapshot and a manifest with the model, temperature, seed and task order,
  so a result table can be traced back to the parameters that produced it.
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from govern import config as config_mod
from govern import run as run_mod
from govern import session as session_mod
from govern import tasks as tasks_mod

from experiments import metrics, spec as spec_mod

RUNS_ROOT = Path("runs")
SNAPSHOT_NAME = "config.snapshot.json"
MANIFEST_NAME = "manifest.json"
FAILURES_NAME = "failures.jsonl"
METRICS_NAME = "metrics.json"

Simulator = Callable[[session_mod.Session, dict], dict]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def plan(spec: spec_mod.Spec, task_list: list[tasks_mod.Task]) -> dict[str, Any]:
    cells = spec.cells(task_list)
    return {
        "run_id": spec.run_id,
        "n_cells": len(cells),
        "conditions": dict(spec.conditions),
        "participants": list(spec.participants),
        "pairs": list(spec.pairs),
        "tasks": [task.task_id for task in task_list],
        "task_order": spec.task_order(task_list),
        "repetitions": spec.repetitions,
        "max_parallel": spec.max_parallel,
        "cells": [cell.key for cell in cells],
    }


def cell_log_path(run_dir: Path, cell: spec_mod.Cell) -> Path:
    return run_dir / "logs" / cell.participant / f"{cell.session_id}.jsonl"


def is_done(log_path: str | Path) -> bool:
    """True when this session's log ends with ``session_end``."""
    path = Path(log_path)
    if not path.is_file():
        return False
    last_type = ""
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    last_type = json.loads(line).get("event_type", "")
                except json.JSONDecodeError:
                    return False  # torn tail: the session did not finish cleanly
    except OSError:
        return False
    return last_type == "session_end"


# ---------------------------------------------------------------------------
# what a run directory must contain before the first session starts
# ---------------------------------------------------------------------------
def write_snapshot(run_dir: Path, spec: spec_mod.Spec) -> Path:
    cfg = config_mod.load()
    payload = {
        "run_id": spec.run_id,
        "written_at": _now(),
        "experiment": spec.raw,
        "config": {
            field: getattr(cfg, field)
            for field in cfg.__dataclass_fields__  # type: ignore[attr-defined]
        },
        "config_path": str(config_mod.DEFAULT_PATH),
    }
    path = run_dir / SNAPSHOT_NAME
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_manifest(run_dir: Path, spec: spec_mod.Spec, task_list: list[tasks_mod.Task]) -> Path:
    cfg = config_mod.load()
    payload = {
        "run_id": spec.run_id,
        "created_at": _now(),
        "app_version": cfg.app_version,
        "model_id": cfg.model_id,
        "model_temperature": cfg.temperature,
        "seed": cfg.seed,
        "mode": "replay",
        "conditions": dict(spec.conditions),
        "participants": list(spec.participants),
        "pairs": list(spec.pairs),
        "repetitions": spec.repetitions,
        "task_order": spec.task_order(task_list),
        "n_cells": len(spec.cells(task_list)),
        "max_parallel": spec.max_parallel,
    }
    path = run_dir / MANIFEST_NAME
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------
def _run_cell(
    run_dir: Path,
    spec: spec_mod.Spec,
    cell: spec_mod.Cell,
    task: tasks_mod.Task,
    simulator: Simulator,
) -> None:
    cfg = config_mod.load()
    logger = run_mod.log_for(run_dir, cell.session_id, cell.participant, cell.condition)
    sess = session_mod.Session(
        run_dir,
        task,
        cell.condition,
        cell.participant,
        logger,
        mode="replay",
        task_index=cell.index,
    )
    started = time.monotonic()
    consent = run_mod.consent_for(cfg, f"EXP-{spec.run_id}")
    simulator(sess, consent)
    run_mod.close_session(sess, started, completed=True)


def _failure_record(spec: spec_mod.Spec, cell: spec_mod.Cell, exc: BaseException) -> dict[str, Any]:
    message = str(exc).replace("\n", " ")
    if len(message) > 300:
        message = message[:299] + "…"
    return {
        "run_id": spec.run_id,
        "cell": cell.key,
        "session_id": cell.session_id,
        "task_id": cell.task_id,
        "pair_id": cell.pair_id,
        "condition": cell.condition,
        "participant": cell.participant,
        "repeat": cell.repeat,
        "error": type(exc).__name__,
        "message": message or "(no message)",
        "at": _now(),
    }


def execute(
    spec: spec_mod.Spec,
    runs_root: str | Path = RUNS_ROOT,
    workers: int | None = None,
    resume: bool = False,
    limit: int | None = None,
    simulate: Simulator | None = None,
) -> dict[str, Any]:
    task_list = spec_mod.load_tasks(spec)
    by_id = {task.task_id: task for task in task_list}
    cells = spec.cells(task_list)
    if limit is not None:
        cells = cells[:limit]
    simulator = simulate or run_mod.rehearse

    run_dir = Path(runs_root) / spec.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    write_snapshot(run_dir, spec)
    write_manifest(run_dir, spec, task_list)

    pending: list[spec_mod.Cell] = []
    skipped = 0
    for cell in cells:
        if resume and is_done(cell_log_path(run_dir, cell)):
            skipped += 1
            continue
        pending.append(cell)

    failures: list[dict[str, Any]] = []
    lock = threading.Lock()

    def work(cell: spec_mod.Cell) -> None:
        try:
            _run_cell(run_dir, spec, cell, by_id[cell.task_id], simulator)
        except Exception as exc:  # noqa: BLE001 - one cell must not stop the batch
            record = _failure_record(spec, cell, exc)
            with lock:
                failures.append(record)
                with (run_dir / FAILURES_NAME).open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())

    parallel = max(1, workers if workers is not None else spec.max_parallel)
    if pending:
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            list(pool.map(work, pending))

    data = metrics.rebuild(run_dir)
    metrics.write(run_dir, data)

    return {
        "run_id": spec.run_id,
        "run_dir": str(run_dir),
        "n_total": len(cells),
        "n_ran": len(pending) - len(failures),
        "n_skipped": skipped,
        "n_failed": len(failures),
        "failures": failures,
        "metrics": data,
        "metrics_path": str(run_dir / METRICS_NAME),
        "max_parallel": parallel,
    }
