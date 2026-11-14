"""Minimal unified-diff applier (standard library only).

The gold patches in ``corpus/`` are ordinary unified diffs. Applying them must
not require ``git`` or ``patch`` to be installed, so this module implements the
subset we generate: ``--- a/path`` / ``+++ b/path`` headers plus ``@@`` hunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(Exception):
    """Raised when a patch is malformed or does not match the target tree."""


@dataclass(frozen=True)
class Hunk:
    old_start: int
    old_len: int
    new_start: int
    new_len: int
    body: tuple[tuple[str, str], ...]


def _strip_prefix(raw: str) -> str:
    path = raw.strip().split("\t")[0].strip()
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def parse(diff_text: str) -> list[tuple[str, list[Hunk]]]:
    """Parse a unified diff into ``[(path, [Hunk, ...]), ...]``."""
    lines = diff_text.splitlines(keepends=True)
    files: list[tuple[str, list[Hunk]]] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith("--- "):
            index += 1
            continue
        old_path = _strip_prefix(lines[index][4:])
        if index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
            raise PatchError(f"missing +++ header after --- {old_path}")
        new_path = _strip_prefix(lines[index + 1][4:])
        path = new_path if new_path != "/dev/null" else old_path
        index += 2
        hunks: list[Hunk] = []
        while index < len(lines) and lines[index].startswith("@@"):
            match = HUNK_RE.match(lines[index])
            if match is None:
                raise PatchError(f"bad hunk header: {lines[index].strip()}")
            old_start = int(match.group(1))
            old_len = int(match.group(2)) if match.group(2) is not None else 1
            new_start = int(match.group(3))
            new_len = int(match.group(4)) if match.group(4) is not None else 1
            index += 1
            body: list[tuple[str, str]] = []
            seen_old = seen_new = 0
            while index < len(lines) and not lines[index].startswith(("@@", "--- ")):
                line = lines[index]
                if line.startswith("\\"):  # "\ No newline at end of file"
                    index += 1
                    continue
                tag, text = line[0], line[1:]
                if tag not in (" ", "-", "+"):
                    break
                body.append((tag, text))
                if tag in (" ", "-"):
                    seen_old += 1
                if tag in (" ", "+"):
                    seen_new += 1
                index += 1
            if seen_old != old_len or seen_new != new_len:
                raise PatchError(
                    f"hunk size mismatch in {path}: expected {old_len}/{new_len}, got {seen_old}/{seen_new}"
                )
            hunks.append(Hunk(old_start, old_len, new_start, new_len, tuple(body)))
        if not hunks:
            raise PatchError(f"no hunks for {path}")
        files.append((path, hunks))
    if not files:
        raise PatchError("no file sections found in diff")
    return files


def changed_files(diff_text: str) -> list[str]:
    """Return the file paths touched by a diff, in diff order."""
    return [path for path, _ in parse(diff_text)]


def _read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def apply_unified_diff(diff_text: str, root: str | Path) -> list[str]:
    """Apply a unified diff to a tree, returning the patched paths."""
    base = Path(root)
    applied: list[str] = []
    for path, hunks in parse(diff_text):
        target = base / path
        if not target.parent.is_dir():
            raise PatchError(f"missing directory for {path}")
        lines = _read_lines(target)
        out: list[str] = []
        cursor = 0
        for hunk in hunks:
            start = hunk.old_start - 1 if hunk.old_len else hunk.old_start
            if start < cursor or start > len(lines):
                raise PatchError(f"hunk out of range for {path} at line {hunk.old_start}")
            out.extend(lines[cursor:start])
            cursor = start
            for tag, text in hunk.body:
                if tag in (" ", "-"):
                    if cursor >= len(lines) or lines[cursor] != text:
                        raise PatchError(f"context mismatch in {path} near line {cursor + 1}")
                    if tag == " ":
                        out.append(lines[cursor])
                    cursor += 1
                else:
                    out.append(text if text.endswith("\n") else text + "\n")
        out.extend(lines[cursor:])
        target.write_text("".join(out), encoding="utf-8", newline="")
        applied.append(path)
    return applied


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m govern.patch")
    parser.add_argument("--apply", nargs=2, metavar=("PATCH", "ROOT"))
    args = parser.parse_args(argv)
    if not args.apply:
        parser.print_help()
        return 2
    patch_path, root = args.apply
    text = Path(patch_path).read_text(encoding="utf-8")
    for path in apply_unified_diff(text, root):
        print(f"patched {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
