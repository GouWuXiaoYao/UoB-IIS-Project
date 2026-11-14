"""Scan the delivery tree for keys and provider endpoints (SPEC M3 acceptance 4).

The patterns are assembled from fragments so that this file does not match
itself, and loopback addresses are allowed because tests need them. Anything
else that looks like a credential or a remote endpoint is a finding.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    ".scratch",
    ".pytest_cache",
    "_tools",
    "_tmp",
    "_pydeps",
    "__pycache__",
    "node_modules",
    "参考代码库",
    # Session data and release artefacts are never committed (SPEC 4.6), and the
    # per-session checkouts under runs/*/work are copies of corpus/ -- scanning
    # them would only report the same files twice.
    "runs",
    "dist",
}
SKIP_SUFFIXES = {".docx", ".png", ".jpg", ".jpeg", ".zip", ".whl", ".pyc"}
# These files *document* the rule and carry synthetic examples inside tests, so
# they would otherwise be their own findings. A real key pasted anywhere else --
# including README and the report -- is still reported.
ALLOWED_PATHS = {
    "AGENTS.md",
    "docs/SPEC.md",
    "tools/scan_secrets.py",
    "tests/test_secrets.py",
}

_PATTERNS = (
    (re.compile(r"\b" + "s" + "k-" + r"[A-Za-z0-9_-]{16,}"), "openai-style key"),
    (re.compile(r"(?i)" + "api" + r"[_-]?key\s*[=:]\s*[\"'][^\"']{8,}[\"']"), "api key assignment"),
    (re.compile(r"(?i)" + "token" + r"\s*=\s*[\"'][^\"']{8,}[\"']"), "token assignment"),
    (re.compile(r"\b" + "ht" + r"tps://[^\s\"')]+"), "remote endpoint"),
)


def _is_loopback(line: str) -> bool:
    return "127.0.0.1" in line or "localhost" in line


def scan_text(text: str, name: str = "<text>") -> list[tuple[str, int, str]]:
    """Return ``(name, line number, line)`` for every hit in ``text``."""
    del name  # the caller already knows which file it handed over
    findings: list[tuple[str, int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern, _label in _PATTERNS:
            if pattern.search(line) and not _is_loopback(line):
                findings.append(("<text>", lineno, line.strip()))
                break
    return findings


def _allowed(path: Path) -> bool:
    posix = path.as_posix()
    return any(posix == name or posix.endswith("/" + name) for name in ALLOWED_PATHS)


def scan_paths(paths, root: str | Path | None = None) -> list[tuple[str, int, str]]:
    """Scan a list of files, skipping binary, ignored directories and doc files.

    When ``root`` is given the ignore rules apply to the path *relative* to it,
    so a repository that happens to live under a directory called ``.scratch``
    is still scanned.
    """
    base = Path(root).resolve() if root is not None else None
    findings: list[tuple[str, int, str]] = []
    for raw in paths:
        path = Path(raw)
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        parts = path.parts
        if base is not None:
            try:
                parts = path.resolve().relative_to(base).parts
            except ValueError:
                parts = path.parts
        if any(part in SKIP_DIRS for part in parts):
            continue
        if _allowed(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for _name, lineno, line in scan_text(text):
            findings.append((str(path), lineno, line))
    return findings


def tracked_files(root: str | Path) -> list[Path]:
    """Every scannable file under ``root``, minus the ignored directories."""
    base = Path(root)
    out: list[Path] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(base).parts):
            continue
        out.append(path)
    return out


def _selftest() -> int:
    root = Path(__file__).resolve().parent.parent
    findings = scan_paths(tracked_files(root), root)
    if findings:
        for path, lineno, line in findings:
            print(f"FAIL: {path}:{lineno}: {line}")
        return 1
    print(f"ok: {len(tracked_files(root))} files scanned, no keys or endpoints")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scan_secrets", description="scan for keys and endpoints")
    parser.add_argument("--root", default=None, help="tree to scan (default: repository root)")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    findings = scan_paths(tracked_files(root), root)
    if args.json:
        print(json.dumps({"findings": [{"path": p, "line": n, "text": t} for p, n, t in findings]}, indent=2))
    else:
        for path, lineno, line in findings:
            print(f"{path}:{lineno}: {line}")
        print(f"{'ok' if not findings else 'FAIL'}: {len(findings)} finding(s) in {len(tracked_files(root))} files")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
