"""M1 acceptance checker for the seed corpus.

For every task in ``corpus/index.json`` this module answers four questions:
does the hidden suite fail on the pristine repository (baseline), does it pass
after the gold patch, are the impact labels complete, and is the repository
free of hints that reveal the answer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from govern import patch, tasks

CORPUS_ROOT = Path("corpus")
SCRATCH_ROOT = Path(__file__).resolve().parent.parent / ".scratch"
LEAK_WORDS = ("gold", "solution", "fixme", "todo", "oracle", "hidden test")
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".cfg", ".ini", ".toml", ""}


@dataclass(frozen=True)
class Check:
    task_id: str
    gold_green: bool
    labels_ok: bool
    leak_free: bool
    baseline_fail_reason: str
    detail: str = ""


def _scratch_dir() -> Path:
    """Create a private scratch directory.

    ``tempfile.mkdtemp`` is avoided on purpose: under the Windows sandbox the
    directories it hands back are not writable by the process that created them.
    """
    SCRATCH_ROOT.mkdir(exist_ok=True)
    target = SCRATCH_ROOT / f"check-{uuid.uuid4().hex[:8]}"
    target.mkdir()
    return target


def scan_leaks(repo: Path) -> list[str]:
    """Return ``file:line`` hits for words that would reveal the answer."""
    hits: list[str] = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            for word in LEAK_WORDS:
                if word in lowered:
                    hits.append(f"{path.relative_to(repo).as_posix()}:{number}: {word}")
    return hits


def _materialise(task: tasks.Task, workdir: Path) -> tuple[Path, Path]:
    target = workdir / "repo"
    shutil.copytree(task.repo, target)
    hidden = workdir / "hidden"
    shutil.copytree(task.hidden_tests, hidden)
    return target, hidden


def _run_hidden(repo: Path, hidden: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(hidden), "-q", "-p", "no:cacheprovider"],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _failure_reason(output: str, returncode: int) -> str:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("E   ") or stripped.startswith("E  "):
            return stripped[1:].strip()
        if "AssertionError" in stripped:
            return stripped
    tail = [ln for ln in output.splitlines() if ln.strip()]
    return tail[-1].strip() if tail else f"pytest exit {returncode}"


def changed_files(diff_text: str) -> list[str]:
    """Return the paths a gold patch touches (thin wrapper over :mod:`govern.patch`)."""
    return patch.changed_files(diff_text)


def _labels_ok(task: tasks.Task) -> tuple[bool, str]:
    path = CORPUS_ROOT / task.task_id / "impact_labels.json"
    if not path.is_file():
        return False, f"missing {path.name}"
    labels = json.loads(path.read_text(encoding="utf-8"))
    if not labels.get("global_vars"):
        return False, "no global_vars entry"
    if not labels.get("cross_module_contracts"):
        return False, "no cross_module_contracts entry"
    diff = task.gold_patch.read_text(encoding="utf-8")
    touched = patch.changed_files(diff)
    if labels.get("files_to_change") != len(touched):
        return False, f"files_to_change={labels.get('files_to_change')} but patch touches {len(touched)}"
    return True, ""


def check_task(task: tasks.Task) -> Check:
    """Run the four M1 acceptance questions for a single task."""
    workdir = _scratch_dir()
    try:
        leaks = scan_leaks(task.repo)

        repo, hidden = _materialise(task, workdir / "baseline")
        code, output = _run_hidden(repo, hidden)
        reason = _failure_reason(output, code)

        gold_dir, gold_hidden = _materialise(task, workdir / "gold")
        diff = task.gold_patch.read_text(encoding="utf-8")
        try:
            patch.apply_unified_diff(diff, gold_dir)
        except patch.PatchError as exc:
            return Check(task.task_id, False, False, not leaks, reason, f"gold patch failed: {exc}")
        gold_code, gold_output = _run_hidden(gold_dir, gold_hidden)

        labels_ok, label_detail = _labels_ok(task)
        detail = label_detail or ("" if gold_code == 0 else _failure_reason(gold_output, gold_code))
        return Check(
            task_id=task.task_id,
            gold_green=gold_code == 0,
            labels_ok=labels_ok,
            leak_free=not leaks,
            baseline_fail_reason=reason,
            detail=detail,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def check_all(root: str | Path = CORPUS_ROOT) -> list[Check]:
    return [check_task(task) for task in tasks.load_index(root)]


def summarise(checks: list[Check]) -> str:
    total = len(checks)
    gold = sum(1 for c in checks if c.gold_green)
    labels = sum(1 for c in checks if c.labels_ok)
    return f"ok: {total} tasks, gold {gold}/{total}, labels {labels}/{total}"


def _selftest() -> int:
    total = 0
    for task in tasks.load_index(CORPUS_ROOT):
        patch.parse(task.gold_patch.read_text(encoding="utf-8"))
        total += 1
    print(f"ok: {total} gold patches parse, 0 leaks required")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m govern.corpus")
    parser.add_argument("--check", action="store_true", help="verify gold, baseline and labels")
    parser.add_argument("--selftest", action="store_true", help="parse gold patches only")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.check:
        parser.print_help()
        return 2

    checks = check_all(CORPUS_ROOT)
    for check in checks:
        status = "ok " if check.gold_green and check.labels_ok and check.leak_free else "FAIL"
        print(
            f"{status} {check.task_id}: gold={check.gold_green} labels={check.labels_ok} "
            f"leak_free={check.leak_free} baseline={check.baseline_fail_reason}"
            + (f" ({check.detail})" if check.detail else "")
        )
    print(summarise(checks))
    healthy = all(c.gold_green and c.labels_ok and c.leak_free for c in checks)
    return 0 if (healthy and checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
