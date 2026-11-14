"""Scratch directories for tests.

``tempfile.TemporaryDirectory`` hands back directories that the Windows sandbox
refuses to write into, so the suite uses a private scratch tree instead.
"""

from __future__ import annotations

import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / ".scratch" / "tests"


@contextmanager
def scratch_dir(name: str = ""):
    """Yield an empty, writable directory that is removed afterwards."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    path = SCRATCH / (name or uuid.uuid4().hex[:10])
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
