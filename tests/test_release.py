"""Acceptance tests for the release snapshot (PLAN milestone M11).

Two identifiers are promised in the README: the commit and a checksum snapshot.
The snapshot is only worth anything if it is (a) reproducible byte for byte and
(b) excludes everything that must never ship — session logs, the local toolchain,
the dev venv and the course material. Both are tested here, together with the
manifest that lets a reviewer verify the bytes without Git.
"""

from __future__ import annotations

import hashlib
import io
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tests._scratch import scratch_dir
from tools import make_release

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = (
    "README.md",
    "AGENTS.md",
    "govern/run.py",
    "govern/provenance.py",
    "config/config.json",
    "docs/SPEC.md",
    "docs/PLAN.md",
    "docs/PROVENANCE.md",
    "tests/test_release.py",
    "storyboards/README.md",
)
FORBIDDEN_PREFIXES = (
    "runs/",
    "dist/",
    ".venv/",
    "_tools/",
    "_tmp/",
    "_pydeps/",
    ".scratch/",
    "__pycache__/",
    "参考代码库/",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _names(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        return archive.namelist()


def _call(*argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        code = make_release.main(list(argv))
    return code, buffer.getvalue()


class ArchiveTests(unittest.TestCase):
    def test_the_archive_holds_the_code_the_docs_and_the_evidence(self):
        with scratch_dir("rel") as tmp:
            zip_path = make_release.build(tmp)
            names = _names(zip_path)
        for wanted in REQUIRED:
            self.assertIn(wanted, names, f"{wanted} is missing from the release")

    def test_the_archive_never_holds_session_data_or_the_toolchain(self):
        with scratch_dir("rel") as tmp:
            names = _names(make_release.build(tmp))
        for name in names:
            for prefix in FORBIDDEN_PREFIXES:
                self.assertFalse(name.startswith(prefix), f"{name} must not ship")
            self.assertFalse(name.endswith((".pyc", ".pyo")), name)
            self.assertFalse(name.endswith(".docx"), name)
            self.assertFalse(name.startswith("DSH-"), name)

    def test_entries_are_sorted_and_carry_a_fixed_timestamp(self):
        with scratch_dir("rel") as tmp:
            zip_path = make_release.build(tmp)
            with zipfile.ZipFile(zip_path) as archive:
                infos = archive.infolist()
        names = [info.filename for info in infos]
        self.assertEqual(names, sorted(names), "a sorted archive is what makes two builds identical")
        for info in infos:
            self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0), f"{info.filename} carries a build timestamp")

    def test_two_builds_are_byte_identical(self):
        with scratch_dir("rel") as first, scratch_dir("rel") as second:
            one = make_release.build(first)
            two = make_release.build(second)
            self.assertEqual(_sha256(one), _sha256(two))

    def test_the_archive_name_carries_the_configured_version(self):
        with scratch_dir("rel") as tmp:
            zip_path = make_release.build(tmp)
        self.assertTrue(zip_path.name.startswith("a2-"), zip_path.name)
        self.assertTrue(zip_path.name.endswith(".zip"), zip_path.name)


class ManifestTests(unittest.TestCase):
    def test_the_manifest_names_the_archive_and_its_digest(self):
        with scratch_dir("rel") as tmp:
            zip_path = make_release.build(tmp)
            sums = make_release.write_manifest(tmp, zip_path)
            text = sums.read_text(encoding="utf-8").strip()
            actual = _sha256(zip_path)
        digest, _, name = text.partition("  ")
        self.assertEqual(name, zip_path.name)
        self.assertEqual(digest, actual)
        self.assertEqual(len(digest), 64)

    def test_verify_accepts_a_fresh_build(self):
        with scratch_dir("rel") as tmp:
            zip_path = make_release.build(tmp)
            make_release.write_manifest(tmp, zip_path)
            problems = make_release.verify(tmp)
        self.assertEqual(problems, [])

    def test_verify_reports_a_tampered_archive(self):
        with scratch_dir("rel") as tmp:
            zip_path = make_release.build(tmp)
            make_release.write_manifest(tmp, zip_path)
            with zip_path.open("ab") as handle:
                handle.write(b"tamper")
            problems = make_release.verify(tmp)
        self.assertTrue(problems, "a rewritten archive must not verify")
        self.assertTrue(any("sha256" in problem for problem in problems), problems)

    def test_verify_reports_a_missing_archive(self):
        with scratch_dir("rel") as tmp:
            (tmp / "SHA256SUMS").write_text("", encoding="utf-8")
            problems = make_release.verify(tmp)
        self.assertTrue(problems)


class CliTests(unittest.TestCase):
    def test_build_prints_the_name_and_the_digest(self):
        with scratch_dir("rel") as tmp:
            code, out = _call("--build", "--dist", str(tmp))
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("ok: a2-"), out)
        self.assertIn("sha256:", out)

    def test_verify_exits_zero_after_a_build(self):
        with scratch_dir("rel") as tmp:
            _call("--build", "--dist", str(tmp))
            code, out = _call("--verify", "--dist", str(tmp))
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("ok: "), out)

    def test_verify_exits_non_zero_on_an_empty_directory(self):
        with scratch_dir("rel") as tmp:
            code, out = _call("--verify", "--dist", str(tmp))
        self.assertEqual(code, 1)
        self.assertIn("SHA256SUMS", out)

    def test_selftest_reports_the_exclusion_rules(self):
        code, out = _call("--selftest")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("ok: "), out)


if __name__ == "__main__":
    unittest.main()
