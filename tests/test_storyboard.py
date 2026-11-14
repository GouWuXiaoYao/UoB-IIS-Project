"""Tests for the fourth storyboard frame: the control path where a suggestion is refused.

The frame is an artefact, so the test checks the artefact's own claims rather than the pixels:
`tools/make_storyboard.py --check` must pass, and the evidence file must still say what the
README says it says. If a future change makes a refusal start editing the working copy, the
re-captured evidence would say so and this test fails.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import make_storyboard  # noqa: E402

PROMISES = ROOT / "storyboards" / "4-c1-reject.promises.txt"


class RefusalEvidenceTests(unittest.TestCase):
    def test_the_check_command_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "make_storyboard.py"), "--check"],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("4 storyboard frame(s)", result.stdout)

    def test_the_evidence_says_the_working_copy_was_untouched(self):
        text = PROMISES.read_text(encoding="utf-8")
        self.assertIn("work tree identical: True", text)
        self.assertRegex(text, r"files hashed: (\d+)   changed after the refusal: 0   added: 0")

    def test_the_evidence_shows_one_rejected_suggestion_and_no_accepted_one(self):
        text = PROMISES.read_text(encoding="utf-8")
        self.assertIn("action=reject", text)
        self.assertIn("n_accepted=0", text)
        self.assertIn("n_rejects=1", text)
        self.assertIn("submitted=False", text)

    def test_the_evidence_cites_a_session_log_that_exists(self):
        text = PROMISES.read_text(encoding="utf-8")
        match = re.search(r"^  seq +(\d+) +suggestion_action", text, re.MULTILINE)
        self.assertIsNotNone(match, "the evidence should cite the seq number of the refusal")
        self.assertGreaterEqual(int(match.group(1)), 2, "the refusal cannot be the first event")

    def test_the_frame_itself_is_present_and_not_a_placeholder(self):
        frame = ROOT / "storyboards" / "4-c1-reject.png"
        self.assertTrue(frame.exists())
        self.assertGreater(frame.stat().st_size, 2000)
        self.assertIn("4-c1-reject.png", make_storyboard.FRAMES)


if __name__ == "__main__":
    unittest.main()
