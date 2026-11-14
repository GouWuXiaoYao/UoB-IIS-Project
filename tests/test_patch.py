"""Tests for the offline unified-diff applier used to apply gold patches."""

from __future__ import annotations

import difflib
import unittest

from _scratch import scratch_dir
from govern.patch import PatchError, apply_unified_diff


def _diff(path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


class ApplyTests(unittest.TestCase):
    def test_applies_single_hunk(self) -> None:
        with scratch_dir() as root:
            (root / "m.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
            text = _diff("m.py", "a = 1\nb = 2\nc = 3\n", "a = 1\nb = 20\nc = 3\n")
            apply_unified_diff(text, root)
            self.assertEqual((root / "m.py").read_text(encoding="utf-8"), "a = 1\nb = 20\nc = 3\n")

    def test_applies_multiple_files_and_hunks(self) -> None:
        with scratch_dir() as root:
            (root / "x.py").write_text("one\ntwo\n", encoding="utf-8")
            (root / "y.py").write_text("red\n", encoding="utf-8")
            text = _diff("x.py", "one\ntwo\n", "one\nTWO\n") + _diff("y.py", "red\n", "blue\n")
            apply_unified_diff(text, root)
            self.assertEqual((root / "x.py").read_text(encoding="utf-8"), "one\nTWO\n")
            self.assertEqual((root / "y.py").read_text(encoding="utf-8"), "blue\n")

    def test_creates_new_file(self) -> None:
        with scratch_dir() as root:
            text = _diff("new.py", "", "print(1)\n")
            apply_unified_diff(text, root)
            self.assertEqual((root / "new.py").read_text(encoding="utf-8"), "print(1)\n")

    def test_rejects_context_mismatch(self) -> None:
        with scratch_dir() as root:
            (root / "m.py").write_text("changed\nheader\n", encoding="utf-8")
            text = _diff("m.py", "a = 1\nb = 2\n", "a = 1\nb = 3\n")
            with self.assertRaises(PatchError):
                apply_unified_diff(text, root)

    def test_rejects_missing_target_directory(self) -> None:
        with scratch_dir() as root:
            text = _diff("nope/m.py", "a\n", "b\n")
            with self.assertRaises(PatchError):
                apply_unified_diff(text, root)


if __name__ == "__main__":
    unittest.main()
