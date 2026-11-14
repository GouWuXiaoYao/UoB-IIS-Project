"""Tests for the report's system diagram.

The diagram is a claim about the code, so the tests check the claim rather than the pixels: every
stage drawn must still exist as a symbol in the file it names, and the shipped PNG must be exactly
what the generator produces.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests._scratch import scratch_dir  # noqa: E402
from tools import make_diagram  # noqa: E402

SHIPPED = ROOT / "System diagram" / "system-diagram.png"


class StageTests(unittest.TestCase):
    def test_every_drawn_stage_names_a_file_that_exists(self):
        missing = [
            name
            for name, (source, _) in make_diagram.NODES.items()
            if not (ROOT / source).exists()
        ]
        self.assertEqual(missing, [])

    def test_every_drawn_stage_names_a_symbol_the_file_still_has(self):
        stale = []
        for name, (source, symbol) in make_diagram.NODES.items():
            if not symbol:
                continue
            if symbol not in (ROOT / source).read_text(encoding="utf-8"):
                stale.append(f"{name}: {symbol!r} not in {source}")
        self.assertEqual(stale, [])

    def test_the_check_command_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "make_diagram.py"), "--check"],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("stages match the source", result.stdout)


class ArtefactTests(unittest.TestCase):
    def test_the_shipped_png_is_a_png_of_the_expected_size(self):
        data = SHIPPED.read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        self.assertEqual((width, height), (1300, 960))

    def test_rebuilding_reproduces_the_shipped_bytes(self):
        with scratch_dir("diagram") as work:
            rebuilt = make_diagram.build(work / "system-diagram.png")
            self.assertEqual(rebuilt.read_bytes(), SHIPPED.read_bytes())

    def test_every_edge_number_is_used_once(self):
        numbers = sorted(make_diagram.EDGES)
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertGreaterEqual(len(numbers), 6, "the figure must show the main data flow")


if __name__ == "__main__":
    unittest.main()
