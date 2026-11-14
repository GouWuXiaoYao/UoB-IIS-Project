"""Read ``conditions.yaml`` and expand it into scheduled cells.

Why a hand-written parser: AGENTS §1 forbids third-party runtime dependencies,
and PyYAML is one. JSON is accepted directly (it is a subset of YAML), and the
block subset below covers what an experiment file needs: nested mappings, block
and inline sequences, comments, quoted strings, and ``int``/``float``/``bool``/
``null`` scalars. Anything outside the subset raises `SpecError` instead of being
guessed at — a run plan that is silently misread is worse than one that refuses
to start.

A *cell* is one session: one task, one condition, one participant, one repetition.
Cells are ordered deterministically so the same file always schedules the same
run in the same order.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from govern import tasks as tasks_mod

CONDITION_CODES = ("C0", "C1")
REQUIRED_CONDITIONS = ("baseline", "governance")


class SpecError(ValueError):
    """The experiment file cannot be read, or describes something impossible."""


# ---------------------------------------------------------------------------
# a small YAML subset
# ---------------------------------------------------------------------------
def parse_yaml(text: str) -> dict[str, Any]:
    """Parse the YAML subset this project writes; JSON is accepted as-is."""
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SpecError(f"not valid JSON: {exc}") from exc

    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        without_comment = _strip_comment(raw)
        if not without_comment.strip():
            continue
        leading = without_comment[: len(without_comment) - len(without_comment.lstrip())]
        if "\t" in leading:
            raise SpecError("tab indentation is not supported; use two spaces")
        lines.append((len(leading), without_comment.strip()))
    if not lines:
        return {}
    if lines[0][0] != 0:
        raise SpecError("the first key must start at column 0")
    value, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise SpecError(f"unexpected content at line {index + 1}: {lines[index][1]!r}")
    if not isinstance(value, dict):
        raise SpecError("the document must be a mapping at the top level")
    return value


def _strip_comment(line: str) -> str:
    quote = ""
    for position, character in enumerate(line):
        if quote:
            if character == quote:
                quote = ""
            continue
        if character in "\"'":
            quote = character
            continue
        if character == "#":
            return line[:position]
    return line


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int):
    if index < len(lines) and lines[index][1].startswith("-"):
        return _parse_list(lines, index, indent)
    return _parse_map(lines, index, indent)


def _parse_map(lines: list[tuple[int, str]], index: int, indent: int):
    out: dict[str, Any] = {}
    while index < len(lines):
        line_indent, text = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise SpecError(f"unexpected indentation at {text!r}")
        if text.startswith("-"):
            break
        key, separator, rest = text.partition(":")
        if not separator or not key.strip():
            raise SpecError(f"expected 'key: value' at {text!r}")
        key = key.strip()
        rest = rest.strip()
        index += 1
        if rest:
            out[key] = _scalar(rest)
            continue
        if index < len(lines) and lines[index][0] > indent:
            child, index = _parse_block(lines, index, lines[index][0])
            out[key] = child
        else:
            out[key] = None
    return out, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int):
    out: list[Any] = []
    while index < len(lines):
        line_indent, text = lines[index]
        if line_indent != indent or not text.startswith("-"):
            break
        item = text[1:].strip()
        index += 1
        if not item:
            if index < len(lines) and lines[index][0] > indent:
                child, index = _parse_block(lines, index, lines[index][0])
                out.append(child)
            else:
                out.append(None)
            continue
        if ":" in item and not item.startswith(("[", "{")):
            key, _, rest = item.partition(":")
            entry: dict[str, Any] = {key.strip(): _scalar(rest.strip()) if rest.strip() else None}
            if index < len(lines) and lines[index][0] > indent:
                more, index = _parse_map(lines, index, lines[index][0])
                entry.update(more)
            out.append(entry)
            continue
        out.append(_scalar(item))
    return out, index


def _scalar(text: str):
    value = text.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [_scalar(part) for part in _split_flow(inner)]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    lowered = value.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    if lowered in ("null", "~", ""):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _split_flow(text: str) -> list[str]:
    parts: list[str] = []
    current = ""
    quote = ""
    for character in text:
        if quote:
            current += character
            if character == quote:
                quote = ""
            continue
        if character in "\"'":
            quote = character
            current += character
            continue
        if character == ",":
            parts.append(current)
            current = ""
            continue
        current += character
    if current.strip():
        parts.append(current)
    return [part.strip() for part in parts if part.strip()]


# ---------------------------------------------------------------------------
# the experiment description
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class Cell:
    """One session: one task, one condition, one participant, one repetition."""

    name: str
    condition: str
    participant: str
    task_id: str
    pair_id: str
    repeat: int
    index: int

    @property
    def key(self) -> str:
        return f"{self.name}|{self.participant}|{self.task_id}|r{self.repeat}"

    @property
    def session_id(self) -> str:
        return f"S-{self.name}-{self.participant}-{self.task_id}-r{self.repeat}"


@dataclasses.dataclass(frozen=True)
class Spec:
    version: int
    run_id: str
    participants: tuple[str, ...]
    conditions: dict[str, str]
    pairs: tuple[str, ...]
    repetitions: int
    max_parallel: int
    raw: dict[str, Any]

    def task_order(self, task_list: list[tasks_mod.Task]) -> list[str]:
        """The order cells are scheduled in: by pair as listed, then task id."""
        order: list[str] = []
        for task in self._ordered(task_list):
            if task.task_id not in order:
                order.append(task.task_id)
        return order

    def _ordered(self, task_list: list[tasks_mod.Task]) -> list[tasks_mod.Task]:
        ranking = {pair: position for position, pair in enumerate(self.pairs)}

        def sort_key(task: tasks_mod.Task) -> tuple[int, str]:
            return ranking.get(task.pair_id, len(ranking)), task.task_id

        return sorted(task_list, key=sort_key)

    def cells(self, task_list: list[tasks_mod.Task]) -> list[Cell]:
        ordered = self._ordered(task_list)
        out: list[Cell] = []
        index = 0
        for repeat in range(self.repetitions):
            for name in sorted(self.conditions):
                condition = self.conditions[name]
                for participant in self.participants:
                    for task in ordered:
                        out.append(
                            Cell(
                                name=name,
                                condition=condition,
                                participant=participant,
                                task_id=task.task_id,
                                pair_id=task.pair_id,
                                repeat=repeat,
                                index=index,
                            )
                        )
                        index += 1
        return out


def load(path: str | Path) -> Spec:
    target = Path(path)
    if not target.is_file():
        raise SpecError(f"no experiment file at {target}")
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise SpecError(f"cannot read {target}: {exc}") from exc
    return validate(parse_yaml(text))


def validate(raw: dict[str, Any]) -> Spec:
    if not isinstance(raw, dict):
        raise SpecError("the experiment file must be a mapping")

    run_id = raw.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise SpecError("run_id must be a non-empty string")
    if any(character in run_id for character in '/\\:*?"<>|'):
        raise SpecError(f"run_id {run_id!r} cannot be used as a directory name")

    participants = raw.get("participants")
    if not isinstance(participants, list) or not participants:
        raise SpecError("participants must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in participants):
        raise SpecError("every participant must be a non-empty string")

    conditions = raw.get("conditions")
    if not isinstance(conditions, dict) or not conditions:
        raise SpecError("conditions must be a non-empty mapping")
    resolved: dict[str, str] = {}
    for name, body in conditions.items():
        if not isinstance(body, dict) or "condition" not in body:
            raise SpecError(f"condition {name!r} needs a 'condition' key")
        code = body["condition"]
        if code not in CONDITION_CODES:
            raise SpecError(f"condition {name!r} uses {code!r}; expected one of {CONDITION_CODES}")
        resolved[str(name)] = str(code)
    missing = [name for name in REQUIRED_CONDITIONS if name not in resolved]
    if missing:
        raise SpecError(f"the comparison needs these conditions: {missing}")

    pairs = raw.get("pairs") or []
    if not isinstance(pairs, list) or not all(isinstance(item, str) for item in pairs):
        raise SpecError("pairs must be a list of pair ids")

    repetitions = raw.get("repetitions", 1)
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions < 1:
        raise SpecError("repetitions must be a positive integer")

    concurrency = raw.get("concurrency") or {}
    if not isinstance(concurrency, dict):
        raise SpecError("concurrency must be a mapping")
    max_parallel = concurrency.get("max_parallel", 1)
    if not isinstance(max_parallel, int) or isinstance(max_parallel, bool) or max_parallel < 1:
        raise SpecError("concurrency.max_parallel must be a positive integer")

    version = raw.get("version", 1)
    if not isinstance(version, int) or isinstance(version, bool):
        raise SpecError("version must be an integer")

    return Spec(
        version=version,
        run_id=run_id,
        participants=tuple(participants),
        conditions=resolved,
        pairs=tuple(pairs),
        repetitions=repetitions,
        max_parallel=max_parallel,
        raw=dict(raw),
    )


def load_tasks(spec: Spec) -> list[tasks_mod.Task]:
    """The task set the spec selects, in scheduling order."""
    available = tasks_mod.load_index()
    if not available:
        raise SpecError("corpus/index.json declares no tasks")
    if spec.pairs:
        unknown = [pair for pair in spec.pairs if not any(task.pair_id == pair for task in available)]
        if unknown:
            raise SpecError(f"no tasks for pair(s) {unknown}")
        selected = [task for task in available if task.pair_id in spec.pairs]
    else:
        selected = list(available)
    if not selected:
        raise SpecError("the spec selects no tasks")
    return spec._ordered(selected)
