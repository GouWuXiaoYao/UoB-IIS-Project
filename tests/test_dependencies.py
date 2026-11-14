"""Dependency discipline: the shipping code imports standard library modules only.

``AGENTS.md`` §1 promises a zero third-party runtime dependency budget. That promise is
worth nothing unless something checks it, so this file parses every import in the
repository and compares the top-level module names against ``sys.stdlib_module_names``.

Two standards, deliberately different:

* shipping code (``govern/``, ``analysis/``, ``experiments/``, ``tools/``) may import the
  standard library and the repository's own modules, and nothing else;
* the test suite may additionally import ``pytest`` and its own helpers, because test-time
  tools are not runtime dependencies. They are pinned in ``requirements-dev.txt``.
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_PACKAGES = {"govern", "analysis", "experiments", "tools"}
#: Helper modules that live next to the tests and are imported by bare name.
LOCAL_HELPERS = {"_scratch", "make_repo", "tests"}
SHIPPING_ROOTS = ("govern", "analysis", "experiments", "tools")
DEV_REQUIREMENTS = ROOT / "requirements-dev.txt"
STDLIB = set(sys.stdlib_module_names)


def _python_files(roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for name in roots:
        base = ROOT / name
        if base.is_dir():
            files.extend(sorted(base.rglob("*.py")))
    return files


def _imported_roots(path: Path) -> set[str]:
    """Return every top-level module name that ``path`` imports."""
    source = path.read_text(encoding="utf-8-sig", errors="replace")
    tree = ast.parse(source, filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # from . import x / from .mod import y
                continue
            if node.module:
                found.add(node.module.split(".")[0])
    return found


def _offenders(roots: tuple[str, ...], allowed: set[str]) -> dict[str, list[str]]:
    offenders: dict[str, list[str]] = {}
    for path in _python_files(roots):
        for name in _imported_roots(path):
            if name not in allowed:
                offenders.setdefault(name, []).append(path.relative_to(ROOT).as_posix())
    return offenders


class ShippingImportTests(unittest.TestCase):
    def test_shipping_code_imports_only_the_standard_library(self) -> None:
        offenders = _offenders(SHIPPING_ROOTS, STDLIB | LOCAL_PACKAGES)
        self.assertEqual(
            {},
            offenders,
            "third-party imports in shipping code: "
            + "; ".join(f"{n} in {sorted(f)}" for n, f in sorted(offenders.items())),
        )

    def test_shipping_code_does_not_import_pytest(self) -> None:
        offenders = [
            path.relative_to(ROOT).as_posix()
            for path in _python_files(SHIPPING_ROOTS)
            if "pytest" in _imported_roots(path)
        ]
        self.assertEqual([], offenders, "pytest is a test-time tool, not a runtime dependency")

    def test_there_is_no_runtime_requirements_file(self) -> None:
        self.assertFalse(
            (ROOT / "requirements.txt").exists(),
            "the runtime has no third-party dependencies, so a runtime requirements file would be a lie",
        )


class TestImportTests(unittest.TestCase):
    def test_the_suite_imports_only_stdlib_local_helpers_and_pytest(self) -> None:
        allowed = STDLIB | LOCAL_PACKAGES | LOCAL_HELPERS | {"pytest"}
        offenders = _offenders(("tests",), allowed)
        self.assertEqual(
            {},
            offenders,
            "unexpected imports in the suite: "
            + "; ".join(f"{n} in {sorted(f)}" for n, f in sorted(offenders.items())),
        )


class DevRequirementsTests(unittest.TestCase):
    def test_dev_tools_are_pinned_exactly(self) -> None:
        self.assertTrue(DEV_REQUIREMENTS.is_file(), "requirements-dev.txt is missing")
        pins = [
            line.split("#", 1)[0].strip()
            for line in DEV_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.split("#", 1)[0].strip()
        ]
        self.assertTrue(pins, "requirements-dev.txt lists nothing")
        for pin in pins:
            self.assertRegex(pin, r"^[A-Za-z0-9._-]+==[0-9]", f"not an exact pin: {pin}")

    def test_the_pinned_pytest_matches_the_installed_one(self) -> None:
        text = DEV_REQUIREMENTS.read_text(encoding="utf-8")
        match = re.search(r"^pytest==(\S+)$", text, re.MULTILINE)
        self.assertIsNotNone(match, "pytest is not pinned in requirements-dev.txt")
        try:
            import pytest
        except ImportError:  # bare python: nothing to compare against
            self.skipTest("pytest is not importable here")
        self.assertEqual(match.group(1), pytest.__version__, "the pin and the installed pytest disagree")


class SourceEncodingTests(unittest.TestCase):
    def test_no_source_file_starts_with_a_byte_order_mark(self) -> None:
        """A BOM breaks ``compile()`` on text and shows up as junk in diffs."""
        offenders = []
        for path in _python_files(SHIPPING_ROOTS + ("tests",)):
            if path.read_bytes()[:3] == b"\xef\xbb\xbf":
                offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual([], offenders, "files starting with a BOM: " + ", ".join(offenders))

    def test_every_source_file_compiles(self) -> None:
        for path in _python_files(SHIPPING_ROOTS + ("tests",)):
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")


class PythonFloorTests(unittest.TestCase):
    def test_readme_states_the_python_floor(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("3.11", text, "README does not state the supported Python version")


if __name__ == "__main__":
    unittest.main()
