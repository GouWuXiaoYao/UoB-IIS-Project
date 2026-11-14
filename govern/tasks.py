"""Task index (corpus/index.json) loading.

M0 only needs the empty-index case; M1 fills in the six seed repositories.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CORPUS_ROOT = Path("corpus")
INDEX_NAME = "index.json"


@dataclass(frozen=True)
class Task:
    task_id: str
    pair_id: str
    stratum: str
    repo: Path
    intent: str
    hidden_tests: Path
    gold_patch: Path
    labels: dict


def load_index(root: str | Path = CORPUS_ROOT) -> list[Task]:
    """Return the tasks declared in the corpus index ([] when absent)."""
    base = Path(root)
    index = base / INDEX_NAME
    if not index.is_file():
        return []
    raw = json.loads(index.read_text(encoding="utf-8"))
    tasks: list[Task] = []
    for entry in raw.get("tasks", []):
        tasks.append(
            Task(
                task_id=entry["task_id"],
                pair_id=entry["pair_id"],
                stratum=entry["stratum"],
                repo=base / entry["task_id"] / "repo",
                intent=entry["intent"],
                hidden_tests=base / entry["task_id"] / "tests_hidden",
                gold_patch=base / entry["task_id"] / "gold.patch",
                labels=entry.get("labels", {}),
            )
        )
    return tasks


def by_id(tasks: list[Task], task_id: str) -> Task:
    for task in tasks:
        if task.task_id == task_id:
            return task
    raise KeyError(f"unknown task_id: {task_id}")
