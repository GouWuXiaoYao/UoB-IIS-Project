"""The secret/endpoint scanner that guards the delivery state (SPEC M3 accept. 4)."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests._scratch import scratch_dir
from tools import scan_secrets

ROOT = Path(__file__).resolve().parent.parent


class PatternTests(unittest.TestCase):
    def test_an_openai_style_key_is_found(self) -> None:
        hits = scan_secrets.scan_text("key = 'sk-abc123def456ghi789jkl'", "x.py")
        self.assertTrue(hits)

    def test_an_api_key_assignment_is_found(self) -> None:
        hits = scan_secrets.scan_text('API_KEY = "abcdef123456"', "x.py")
        self.assertTrue(hits)

    def test_a_token_assignment_is_found(self) -> None:
        self.assertTrue(scan_secrets.scan_text('token="deadbeef"', "x.py"))

    def test_an_https_endpoint_is_found(self) -> None:
        self.assertTrue(scan_secrets.scan_text('BASE = "https://api.example.com/v1"', "x.py"))

    def test_loopback_http_is_allowed(self) -> None:
        self.assertEqual(scan_secrets.scan_text('BASE = "http://127.0.0.1:8000/v1"', "x.py"), [])
        self.assertEqual(scan_secrets.scan_text('BASE = "http://localhost:8000/v1"', "x.py"), [])

    def test_a_plain_sentence_is_clean(self) -> None:
        self.assertEqual(scan_secrets.scan_text("the model writes a patch", "x.py"), [])

    def test_the_scanner_does_not_flag_itself(self) -> None:
        self.assertEqual(scan_secrets.scan_text(Path(scan_secrets.__file__).read_text(encoding="utf-8"), "scan_secrets.py"), [])


class RepositoryTests(unittest.TestCase):
    def test_the_repository_is_clean(self) -> None:
        findings = scan_secrets.scan_paths(scan_secrets.tracked_files(ROOT))
        self.assertEqual(findings, [], "\n".join(f"{f}:{n}: {line}" for f, n, line in findings))

    def test_ignored_directories_are_not_scanned(self) -> None:
        with scratch_dir() as tmp:
            hidden = tmp / ".venv" / "x.py"
            hidden.parent.mkdir(parents=True)
            hidden.write_text('KEY = "sk-abc123def456ghi789jkl"', encoding="utf-8")
            visible = tmp / "real.py"
            visible.write_text("print(1)\n", encoding="utf-8")
            found = scan_secrets.scan_paths([visible, hidden])
            self.assertEqual([Path(f).name for f, _, _ in found], [])


class CliTests(unittest.TestCase):
    def test_clean_repository_exits_zero(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = scan_secrets.main(["--root", str(ROOT)])
        self.assertEqual(code, 0, buffer.getvalue())
        self.assertIn("ok:", buffer.getvalue())

    def test_a_finding_exits_non_zero(self) -> None:
        with scratch_dir() as tmp:
            (tmp / "leak.py").write_text('K = "sk-abc123def456ghi789jkl"\n', encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = scan_secrets.main(["--root", str(tmp)])
            self.assertEqual(code, 1)
            self.assertIn("leak.py", buffer.getvalue())

    def test_json_output_lists_every_finding(self) -> None:
        with scratch_dir() as tmp:
            (tmp / "leak.py").write_text('K = "https://api.example.com"\n', encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                scan_secrets.main(["--root", str(tmp), "--json"])
            payload = json.loads(buffer.getvalue())
            self.assertEqual(len(payload["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
