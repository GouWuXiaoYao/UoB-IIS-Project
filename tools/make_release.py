"""Build and verify the release snapshot (PLAN milestone M11).

The README promises two identifiers: a commit and a checksum snapshot. This tool
produces the second one:

    python tools/make_release.py --build      # dist/a2-<version>.zip + SHA256SUMS
    python tools/make_release.py --verify     # re-hash the archive, compare
    python tools/make_release.py --selftest

Two properties matter and are both tested in ``tests/test_release.py``:

* **Reproducible** — entries are sorted and carry a fixed timestamp, so the same
  tree always produces the same bytes. Without that, "the snapshot" identifies a
  build machine, not the work.
* **Nothing that must not ship** — session logs (``runs/``), the local toolchain
  (``_tools/``), the dev venv, scratch space and the course material are excluded
  by rule, not by remembering to delete them.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DIST = ROOT / "dist"
MANIFEST = "SHA256SUMS"

SKIP_DIRS = {
    "runs", "dist", ".venv", "_tools", "_tmp", "_pydeps", ".scratch",
    "__pycache__", ".git", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    "参考代码库", "node_modules",
}
SKIP_SUFFIXES = (".pyc", ".pyo", ".tmp", ".docx", ".zip")
SKIP_NAMES = {
    "pip-install.log", "winget.log", "venv.log", ".env",
}
SKIP_PREFIXES = ("A2_API_KEY", "DSH-", "pytest-cache-files-")

FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def version() -> str:
    """The version stamped into the archive name; config is the only source."""
    from govern import config

    return config.load().app_version


def _skip(relative: Path) -> bool:
    if any(part in SKIP_DIRS for part in relative.parts[:-1]):
        return True
    if relative.parts and relative.parts[0] in SKIP_DIRS:
        return True
    name = relative.name
    if name in SKIP_NAMES:
        return True
    if name.endswith(SKIP_SUFFIXES):
        return True
    if name.startswith(SKIP_PREFIXES):
        return True
    return False


def payload(root: Path = ROOT) -> list[tuple[str, bytes]]:
    """Every file that ships, as ``(posix name, bytes)``, sorted by name."""
    entries: list[tuple[str, bytes]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if _skip(relative):
            continue
        entries.append((relative.as_posix(), path.read_bytes()))
    entries.sort(key=lambda pair: pair[0])
    return entries


def archive_name(version_string: str | None = None) -> str:
    return f"a2-{version_string or version()}.zip"


def build(dist: str | Path = DIST) -> Path:
    """Write the archive into ``dist`` and return its path."""
    target = Path(dist)
    target.mkdir(parents=True, exist_ok=True)
    zip_path = target / archive_name()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in payload():
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return zip_path


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(dist: str | Path, zip_path: Path) -> Path:
    """Write ``<sha256>  <name>`` — the format ``sha256sum -c`` understands."""
    path = Path(dist) / MANIFEST
    path.write_text(f"{sha256_of(zip_path)}  {zip_path.name}\n", encoding="utf-8")
    return path


def verify(dist: str | Path = DIST) -> list[str]:
    """Return every problem with the snapshot in ``dist``."""
    target = Path(dist)
    manifest = target / MANIFEST
    if not manifest.exists():
        return [f"{manifest.name} is missing from {target}"]
    lines = [line.strip() for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return [f"{manifest.name} lists no archive"]
    problems: list[str] = []
    for line in lines:
        digest, _, name = line.partition("  ")
        if not name:
            problems.append(f"{manifest.name}: cannot parse line {line!r}")
            continue
        archive = target / name
        if not archive.exists():
            problems.append(f"{name} listed in {manifest.name} but missing")
            continue
        actual = sha256_of(archive)
        if actual != digest:
            problems.append(f"{name}: sha256 mismatch (manifest {digest[:12]}…, actual {actual[:12]}…)")
    return problems


def _selftest() -> int:
    entries = payload()
    names = [name for name, _ in entries]
    if names != sorted(names):
        print("fail: the payload is not sorted", file=sys.stderr)
        return 1
    leaked = [name for name in names if _skip(Path(name))]
    if leaked:
        print(f"fail: {len(leaked)} excluded path(s) would ship, e.g. {leaked[0]}", file=sys.stderr)
        return 1
    digest = hashlib.sha256()
    for name, data in entries:
        digest.update(name.encode("utf-8"))
        digest.update(data)
    print(
        f"ok: {len(names)} files, {len(SKIP_DIRS)} directory rules, "
        f"{len(SKIP_SUFFIXES) + len(SKIP_NAMES)} file rules, tree digest {digest.hexdigest()[:12]}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python tools/make_release.py")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--build", action="store_true", help="write the archive and manifest")
    group.add_argument("--verify", action="store_true", help="re-hash the archive against the manifest")
    group.add_argument("--selftest", action="store_true", help="check the exclusion rules")
    parser.add_argument("--dist", default=str(DIST), help="output directory (default: dist/)")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.build:
        zip_path = build(args.dist)
        write_manifest(args.dist, zip_path)
        print(f"ok: {zip_path.name} sha256:{sha256_of(zip_path)}")
        return 0
    if args.verify:
        problems = verify(args.dist)
        if problems:
            print(f"fail: {len(problems)} problem(s) with the snapshot", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        print(f"ok: {MANIFEST} matches the archive in {args.dist}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
