"""Author-simulated model recordings (M6).

There is no API key at build time, so the six recordings that ship with the
repository are *simulated*: the factory starts from the gold patch and drops the
last file section, so each suggestion fixes the main module and misses one
consumer. That is the failure mode the assessment card exists to surface (A1
section 4: cross-module side effects that only show up downstream), and every
recording carries ``"source": "sim"`` so nobody mistakes it for real model
output.

The factory is deterministic: ``build()`` twice returns identical bytes, and
``--selftest`` re-derives the shipped files and compares them byte for byte.

Usage:
    python tools/make_recordings.py --write     # (re)generate recordings/
    python tools/make_recordings.py --selftest  # verify the shipped files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from govern import config as config_mod  # noqa: E402
from govern import llm  # noqa: E402
from govern import patch as patch_mod  # noqa: E402
from govern import tasks as tasks_mod  # noqa: E402

RECORDINGS = ROOT / "recordings"

RATIONALE = (
    "Convert the amounts to integer minor units inside the module and let the "
    "caller apply tax once. {files} is the module that owns the state."
)

LAYERS = {
    "L1": "state: amounts are stored as integer minor units",
    "L2": "call sites: tax is added once, at the reporting boundary",
}


def _sections(diff: str) -> list[str]:
    """Split a unified diff into one block per file (headers included)."""
    blocks: list[str] = []
    current: list[str] = []
    for line in diff.splitlines(keepends=True):
        if line.startswith("--- ") and any(part.startswith("+++ ") for part in current):
            blocks.append("".join(current))
            current = []
        current.append(line)
    if current:
        blocks.append("".join(current))
    return [block for block in blocks if any(line.startswith("+++ ") for line in block.splitlines())]


def suggest(task: tasks_mod.Task) -> dict:
    """The simulated reply for one task: the gold patch minus one consumer."""
    diff = task.gold_patch.read_text(encoding="utf-8")
    blocks = _sections(diff)
    if not blocks:
        raise SystemExit(f"{task.task_id}: gold.patch has no file section")
    partial = blocks[:-1] if len(blocks) > 1 else blocks
    partial_diff = "".join(partial)
    patch_mod.parse(partial_diff)  # a reply that is not a usable diff is a bug here

    ctx = llm.Context.for_task(task)
    changed = {name.split("/")[0] for name in patch_mod.changed_files(partial_diff)}
    touched = [symbol for symbol in ctx.symbols if symbol.split(".")[0] in changed]
    modules = sorted({symbol.rsplit(".", 1)[0] for symbol in touched})
    return {
        "patch_diff": partial_diff,
        "rationale_text": RATIONALE.format(files=", ".join(modules) or "the module"),
        "touched_symbols": touched,
        "layers": dict(LAYERS),
    }


def recording(task: tasks_mod.Task, cfg: config_mod.Config) -> tuple[str, bytes]:
    """The repository-relative path and exact bytes of one recording."""
    ctx = llm.Context.for_task(task)
    slug = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in cfg.model_id)
    rel = f"{slug}/{ctx.sha256()}.json"
    body = {
        "format": llm.RECORDING_FORMAT,
        "source": "sim",
        "request_sha256": f"sha256:{ctx.sha256()}",
        "model_id": cfg.model_id,
        "model_temperature": cfg.temperature,
        "seed": cfg.seed,
        "latency_ms": 0,
        "response": suggest(task),
    }
    return rel, (json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build(cfg: config_mod.Config | None = None, corpus_root: Path = tasks_mod.CORPUS_ROOT) -> dict[str, bytes]:
    """Every recording the repository ships, keyed by path under recordings/."""
    conf = cfg or config_mod.load(ROOT / "config" / "config.json")
    base = corpus_root if corpus_root.is_absolute() else ROOT / corpus_root
    out: dict[str, bytes] = {}
    for task in tasks_mod.load_index(base):
        rel, blob = recording(task, conf)
        out[rel] = blob
    return out


def write(cfg: config_mod.Config | None = None) -> list[Path]:
    """Write every recording, returning the paths written."""
    written: list[Path] = []
    for rel, blob in sorted(build(cfg).items()):
        path = RECORDINGS / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        written.append(path)
    return written


def selftest() -> int:
    """The shipped recordings must be exactly what the factory produces."""
    built = build()
    if not built:
        print("FAIL: no tasks in the corpus index")
        return 1
    problems: list[str] = []
    for rel, blob in sorted(built.items()):
        path = RECORDINGS / rel
        if not path.is_file():
            problems.append(f"missing: {path.relative_to(ROOT).as_posix()}")
        elif path.read_bytes() != blob:
            problems.append(f"differs: {path.relative_to(ROOT).as_posix()}")
    extra = {
        path.relative_to(RECORDINGS).as_posix()
        for path in RECORDINGS.rglob("*.json")
    } - set(built)
    for name in sorted(extra):
        problems.append(f"unexpected: recordings/{name}")
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    print(f"ok: {len(built)} recordings match the factory")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="make_recordings", description="simulated LLM recordings")
    parser.add_argument("--write", action="store_true", help="write recordings/")
    parser.add_argument("--selftest", action="store_true", help="verify the shipped files")
    args = parser.parse_args(argv)
    if args.write:
        for path in write():
            print(f"wrote {path.relative_to(ROOT).as_posix()}")
        return 0
    if args.selftest:
        return selftest()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
