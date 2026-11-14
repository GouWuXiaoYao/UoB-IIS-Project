"""Tests for the report builder and the report mode of the word counter.

The report is a deliverable, so the things that can silently go wrong are checked rather
than eyeballed: the counts against the marking limits, the stated counts against the
text, the styles actually used, and the fact that a rebuild is byte-identical.
"""

from __future__ import annotations

import io
import subprocess
import sys
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

import tools.make_report as make_report
import tools.word_count as word_count
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
SHIPPED = ROOT / "docs" / "A2_Report_3138100.docx"


def quiet(function, *args, **kwargs):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = function(*args, **kwargs)
    return code, buffer.getvalue()


class CountTests(unittest.TestCase):
    def test_the_abstract_and_body_are_within_the_marking_limits(self):
        counts = make_report.section_counts()
        self.assertLessEqual(counts["abstract"], 300)
        self.assertLessEqual(counts["body"], 1100)
        self.assertLessEqual(counts["total"], 1400)

    def test_the_body_is_near_the_target_rather_than_far_under_it(self):
        # The brief asks for about 1,000 words; 800 would be a thin answer.
        self.assertGreaterEqual(make_report.section_counts()["body"], 950)

    def test_captions_and_references_are_not_counted(self):
        with_extra = make_report.section_counts(
            make_report.BLOCKS
            + [("caption", "Figure 9. " + "word " * 80), ("ref", "Doe, J. (2026) " + "word " * 80)]
        )
        plain = make_report.section_counts()
        self.assertEqual(with_extra, plain)

    def test_table_cells_are_counted(self):
        rows = [["one two", "three four", "five", "six"]]
        with_cells = make_report.section_counts(make_report.BLOCKS + [("table", rows)])
        self.assertEqual(with_cells["body"], make_report.section_counts()["body"] + 6)


class BuildTests(unittest.TestCase):
    def test_a_rebuild_is_byte_identical(self):
        with scratch_dir() as scratch:
            first = make_report.build(scratch / "a.docx")
            second = make_report.build(scratch / "b.docx")
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_the_document_uses_real_style_ids(self):
        # A block style such as "counts" must be mapped to a styleId that exists; using
        # the block name directly is what once produced KeyError and a corrupt archive.
        with scratch_dir() as scratch:
            path = make_report.build(scratch / "r.docx")
            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
                styles = archive.read("word/styles.xml").decode("utf-8")
        used = set(__import__("re").findall(r'w:pStyle w:val="([^"]+)"', xml))
        declared = set(__import__("re").findall(r'w:styleId="([^"]+)"', styles))
        self.assertTrue(used)
        self.assertLessEqual(used, declared, f"undeclared styles: {sorted(used - declared)}")

    def test_the_shipped_report_matches_a_fresh_build(self):
        with scratch_dir() as scratch:
            built = make_report.build(scratch / "r.docx")
            self.assertEqual(built.read_bytes(), SHIPPED.read_bytes())


class CheckModeTests(unittest.TestCase):
    def test_the_shipped_report_passes_the_checker(self):
        code, output = quiet(word_count.main, [f"--docx={SHIPPED}", "--check"])
        self.assertEqual(code, 0, output)
        self.assertIn("ok: the stated counts match the text", output)

    def test_a_wrong_stated_count_is_refused(self):
        with scratch_dir() as scratch:
            path = scratch / "r.docx"
            path.write_bytes(SHIPPED.read_bytes())
            xml = word_count.docx_paragraphs(path)
            stated = [
                text for style, text in xml if style.lower() == "counts"
            ][0]
            broken = stated.replace("total", "total").replace("abstract", "abstract")
            replacement = broken.replace("Word count:", "Word count: 1")
            data = _rewrite(path, stated, replacement)
            self.assertIn(b"Word count: 1", data)
            code, output = quiet(word_count.main, [f"--docx={path}", "--check"])
            self.assertEqual(code, 1, output)
            self.assertIn("fail:", output)

    def test_a_report_without_a_stated_count_is_refused(self):
        with scratch_dir() as scratch:
            path = scratch / "r.docx"
            path.write_bytes(SHIPPED.read_bytes())
            stated = [text for style, text in word_count.docx_paragraphs(path) if style.lower() == "counts"][0]
            _rewrite(path, stated, "Counts omitted on purpose.")
            code, output = quiet(word_count.main, [f"--docx={path}", "--check"])
            self.assertEqual(code, 1, output)
            self.assertIn("does not state its word count", output)

    def test_the_command_runs_from_the_shell(self):
        result = subprocess.run(
            [sys.executable, "tools/word_count.py", f"--docx={SHIPPED}", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def _rewrite(path: Path, old: str, new: str) -> bytes:
    """Replace one paragraph's text inside the document part, keeping the archive valid."""
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    xml = parts["word/document.xml"].decode("utf-8")
    xml = xml.replace(old, new, 1)
    parts["word/document.xml"] = xml.encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    path.write_bytes(buffer.getvalue())
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
