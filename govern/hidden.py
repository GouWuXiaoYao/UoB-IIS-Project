"""Run a hidden test suite in a child interpreter, with no third-party imports.

The hidden suites are plain functions (``def test_x(): assert ...``), so a
standard-library runner is enough -- and it has to be, because AGENTS.md 1.1
forbids a runtime dependency on pytest. The child process is also the sandbox:
a suite that hangs is killed by the timeout, and a suite that calls
``sys.exit``/raises at import time is reported as a failure rather than taking
the session down with it (SPEC M8 acceptance 4).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

#: Child interpreter: import each ``test_*.py``, call every ``test_*`` callable,
#: print one JSON object. Failures carry ``file::test: Type: message``.
RUNNER = r"""
import importlib.util, json, sys
from pathlib import Path

hidden = Path(sys.argv[1])
n, failures = 0, []
for path in sorted(hidden.glob("test_*.py")):
    name = "hidden_" + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except BaseException as exc:
        failures.append("%s::<import>: %s: %s" % (path.name, type(exc).__name__, exc))
        continue
    for attr in sorted(a for a in dir(module) if a.startswith("test_")):
        fn = getattr(module, attr)
        if not callable(fn):
            continue
        n += 1
        try:
            fn()
        except BaseException as exc:
            failures.append("%s::%s: %s: %s" % (path.name, attr, type(exc).__name__, exc))
print(json.dumps({"n": n, "failures": failures}))
"""


def run(repo: str | Path, hidden: str | Path, timeout_s: int) -> tuple[int, list[str], int]:
    """Run one hidden suite.

    Returns ``(code, failures, n_tests)`` where ``code`` is 0 when every test
    passed, 1 when at least one failed and 2 when the suite did not finish
    (timeout, crash or unparsable output).
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(repo).resolve())
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with subprocess.Popen(
        [sys.executable, "-c", RUNNER, str(Path(hidden).resolve())],
        cwd=str(repo),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        try:
            produced, errors = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # reap the child and close the pipes
            return 2, [f"timeout: suite exceeded {timeout_s}s"], 0
    if proc.returncode != 0:
        tail = (produced + errors).strip().splitlines()
        return 2, [f"runner exit {proc.returncode}: {tail[-1] if tail else 'no output'}"], 0
    try:
        payload = json.loads(produced.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return 2, ["runner produced no JSON report"], 0
    failures = [str(item) for item in payload.get("failures", [])]
    n = int(payload.get("n", 0))
    if failures:
        return 1, failures, n
    if n == 0:
        return 2, ["suite contains no test_* functions"], 0
    return 0, [], n


def _selftest() -> int:
    import shutil

    root = Path(__file__).resolve().parent.parent / ".scratch"
    root.mkdir(parents=True, exist_ok=True)
    work = root / "hidden-selftest"
    shutil.rmtree(work, ignore_errors=True)
    (work / "suite").mkdir(parents=True)
    (work / "suite" / "test_ok.py").write_text("def test_a():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    code, failures, n = run(work, work / "suite", 30)
    if (code, failures, n) != (0, [], 1):
        print(f"FAIL: passing suite returned {code}, {failures}, {n}")
        return 1
    (work / "suite" / "test_bad.py").write_text(
        "def test_b():\n    assert False, 'boom'\n", encoding="utf-8"
    )
    code, failures, n = run(work, work / "suite", 30)
    if code != 1 or n != 2 or not any("boom" in f for f in failures):
        print(f"FAIL: failing suite returned {code}, {failures}, {n}")
        return 1
    print("ok: hidden suite runner reports pass/fail in a child interpreter")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="hidden", description="hidden suite runner")
    parser.add_argument("--selftest", action="store_true", help="verify the runner itself")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
