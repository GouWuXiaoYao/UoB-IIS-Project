"""M7 = SPEC M8: the outcome scorer.

Two halves, both offline and deterministic:

* **the six-rule JSON rule set** (`config/rules.json`, Q6) turns "is this
  refactor any good" into weighted counts of machine-detectable debt, and
* **the hidden suite** decides whether the refactor is functionally correct.

``debt_delta``/``vuln_delta`` are *after minus before*: the baseline is taken on
the task's seed repository, so a suggestion that removes a smell has a negative
delta. ``vuln_delta`` only counts the last three categories (``hardcoded_secret``,
``eval_usage``, ``sql_concat``) -- the three that are exploitable, not merely
expensive to maintain.

``is_correct`` (SPEC M8 acceptance 6, stated here rather than implied by code):
a suggestion is correct **iff applying it reduces the number of failing hidden
tests**, i.e. ``after.n_fail < before.n_fail``. Passing the whole suite is the
strongest case of that; a suggestion that merely shortens the code is not
correct.

Rules never run inside the session process: the hidden suite is executed in a
child interpreter with a hard timeout (SPEC M8 acceptance 4), so a hanging or
crashing repository cannot take the session down with it.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from govern import config as config_mod
from govern import hidden as hidden_mod
from govern import tasks as tasks_mod

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / "config" / "rules.json"
SCORER_VERSION = "score/1.0.0"

#: The three categories that are security-relevant, not merely costly.
VULN_CATEGORIES = frozenset({"hardcoded_secret", "eval_usage", "sql_concat"})

#: Directories that are never scored: generated caches and the project's own tests.
SKIP_DIRS = frozenset({"__pycache__", "tests", ".git", ".venv", "_tools"})

BRANCH_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)

@dataclass(frozen=True)
class Finding:
    """One rule hit. ``line`` is 1-based and points at the offending statement."""

    rule_id: str
    path: str
    line: int
    detail: str


@dataclass(frozen=True)
class Outcome:
    """What the scorer knows about a submitted repository (SPEC M8 output)."""

    tests_pass: bool
    n_fail: int
    failing_tests: list[str]
    debt_delta: float
    vuln_delta: int
    lines_added: int
    lines_removed: int
    scorer_version: str

    def as_dict(self) -> dict:
        return {
            "tests_pass": self.tests_pass,
            "n_fail": self.n_fail,
            "failing_tests": list(self.failing_tests),
            "debt_delta": self.debt_delta,
            "vuln_delta": self.vuln_delta,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "scorer_version": self.scorer_version,
        }


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------
def load_rules(path: str | Path = RULES_PATH) -> dict:
    """Read and sanity-check the rule set."""
    rules = json.loads(Path(path).read_text(encoding="utf-8"))
    for rule in rules["rules"]:
        for key in ("rule_id", "category", "severity", "weight"):
            if key not in rule:
                raise ValueError(f"rule {rule.get('rule_id')!r} is missing {key!r}")
    return rules


def rules_hash(rules: dict) -> str:
    """Stable digest of the rule set; changes whenever a threshold changes."""
    blob = json.dumps(rules, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def scorer_version(rules: dict) -> str:
    """``score/1.0.0+sha256:...`` -- the code version *and* the rule set (SPEC M8-3)."""
    return f"{SCORER_VERSION}+{rules_hash(rules)}"


def _rule(rules: dict, rule_id: str) -> dict:
    for rule in rules["rules"]:
        if rule["rule_id"] == rule_id:
            return rule
    raise KeyError(f"unknown rule: {rule_id}")


def debt(counts: dict[str, int], rules: dict) -> int:
    """Weighted sum over every category."""
    return sum(_rule(rules, rule_id)["weight"] * n for rule_id, n in counts.items())


def vuln(counts: dict[str, int], rules: dict) -> int:
    """Weighted sum over the security-relevant categories only."""
    return sum(
        _rule(rules, rule_id)["weight"] * n
        for rule_id, n in counts.items()
        if _rule(rules, rule_id)["category"] in VULN_CATEGORIES
    )


# ---------------------------------------------------------------------------
# scanning
# ---------------------------------------------------------------------------
def _complexity(tree: ast.AST, rule: dict) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    max_lines = rule["max_function_lines"]
    max_depth = rule["max_branch_depth"]
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        length = end - node.lineno + 1
        if length > max_lines:
            out.append((node.lineno, f"{node.name}() spans {length} lines (limit {max_lines})"))
        depth = _branch_depth(node)
        if depth > max_depth:
            out.append((node.lineno, f"{node.name}() branches {depth} deep (limit {max_depth})"))
    return out


def _branch_depth(node: ast.AST, depth: int = 0) -> int:
    """Deepest nesting of branch statements inside ``node`` (its own body counts)."""
    best = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, BRANCH_NODES):
            best = max(best, _branch_depth(child, depth + 1))
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # nested functions are scored on their own
        else:
            best = max(best, _branch_depth(child, depth))
    return best


def _dup_findings(files: dict[str, list[str]], rule: dict) -> list[Finding]:
    """Windows of ``block_lines`` normalised lines that occur more than once."""
    size = rule["block_lines"]
    allowed = rule["max_occurrences"]
    seen: dict[tuple[str, ...], list[tuple[str, int]]] = {}
    for path, lines in sorted(files.items()):
        cooked = []
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            cooked.append((lineno, stripped))
        for start in range(len(cooked) - size + 1):
            window = tuple(text for _, text in cooked[start : start + size])
            seen.setdefault(window, []).append((path, cooked[start][0]))
    out: list[Finding] = []
    flagged: dict[str, list[int]] = {}
    for window, places in seen.items():
        if len(places) <= allowed:
            continue
        for path, line in places[allowed:]:
            near = flagged.setdefault(path, [])
            if any(abs(line - other) < size for other in near):
                continue  # overlapping windows of a block already reported
            near.append(line)
            out.append(Finding("duplication", path, line, f"{size} repeated lines"))
    return out


def _bare_except(tree: ast.AST) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            out.append((node.lineno, "bare except swallows every error"))
    return out


def _hardcoded_secret(tree: ast.AST, rule: dict) -> list[tuple[int, str]]:
    name_re = re.compile(rule["secret_name_pattern"])
    min_len = rule["min_secret_length"]
    prefixes = tuple(rule["secret_prefixes"])
    out: list[tuple[int, str]] = []

    def consider(value: str, lineno: int, name: str) -> None:
        if not isinstance(value, str) or len(value) < min_len:
            return
        if value.startswith(prefixes) or name_re.search(name):
            out.append((lineno, f"literal credential assigned to {name or 'value'}"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                label = getattr(target, "id", "") or getattr(target, "attr", "")
                consider(node.value.value, node.lineno, label or "")
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Constant):
            label = getattr(node.target, "id", "") or getattr(node.target, "attr", "")
            consider(node.value.value, node.lineno, label or "")
        elif isinstance(node, (ast.keyword,)) and isinstance(node.value, ast.Constant):
            consider(node.value.value, node.value.lineno, node.arg or "")
    return out


def _forbidden_calls(tree: ast.AST, rule: dict) -> list[tuple[int, str]]:
    banned = set(rule["forbidden_calls"])
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in banned:
            out.append((node.lineno, f"{node.func.id}() executes data as code"))
    return out


def _mentions_sql(text: str, keywords: list[str]) -> bool:
    upper = text.upper()
    return any(keyword in upper for keyword in keywords)


def _sql_concat(tree: ast.AST, rule: dict) -> list[tuple[int, str]]:
    keywords = rule["sql_keywords"]
    out: list[tuple[int, str]] = []

    def literal(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = literal(node.left), literal(node.right)
            if left and _mentions_sql(left, keywords) and not right:
                out.append((node.lineno, "SQL built by concatenation"))
            elif right and _mentions_sql(right, keywords) and not left:
                out.append((node.lineno, "SQL built by concatenation"))
        elif isinstance(node, ast.JoinedStr):
            text = "".join(
                part.value for part in node.values if isinstance(part, ast.Constant) and isinstance(part.value, str)
            )
            if _mentions_sql(text, keywords):
                out.append((node.lineno, "SQL built by f-string interpolation"))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "format":
                text = literal(node.func.value)
                if text and _mentions_sql(text, keywords):
                    out.append((node.lineno, "SQL built by str.format"))
    return out


def scan_source(text: str, path: str, rules: dict) -> list[Finding]:
    """Every finding in one source file (rules that work per file)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out: list[Finding] = []
    for rule in rules["rules"]:
        category = rule["category"]
        if category == "complexity":
            for line, detail in _complexity(tree, rule):
                out.append(Finding(rule["rule_id"], path, line, detail))
        elif category == "bare_except":
            for line, detail in _bare_except(tree):
                out.append(Finding(rule["rule_id"], path, line, detail))
        elif category == "hardcoded_secret":
            for line, detail in _hardcoded_secret(tree, rule):
                out.append(Finding(rule["rule_id"], path, line, detail))
        elif category == "eval_usage":
            for line, detail in _forbidden_calls(tree, rule):
                out.append(Finding(rule["rule_id"], path, line, detail))
        elif category == "sql_concat":
            for line, detail in _sql_concat(tree, rule):
                out.append(Finding(rule["rule_id"], path, line, detail))
        elif category == "duplication":
            out.extend(_dup_findings({path: text.splitlines()}, rule))
        else:
            raise KeyError(f"unknown rule category: {category}")
    return sorted(out, key=lambda finding: (finding.path, finding.line, finding.rule_id))


def _python_files(repo: Path) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {}
    for path in sorted(repo.rglob("*.py")):
        relative = path.relative_to(repo)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        try:
            files[relative.as_posix()] = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
    return files


def scan_repo(repo: str | Path, rules: dict) -> list[Finding]:
    """Every finding in a repository; file order never changes the result."""
    base = Path(repo)
    files = _python_files(base)
    out: list[Finding] = []
    per_file = {rule["rule_id"] for rule in rules["rules"]} - {"duplication"}
    for path, lines in files.items():
        text = "\n".join(lines) + "\n"
        out.extend(f for f in scan_source(text, path, rules) if f.rule_id in per_file)
    for rule in rules["rules"]:
        if rule["category"] == "duplication":
            out.extend(_dup_findings(files, rule))
    return sorted(out, key=lambda finding: (finding.path, finding.line, finding.rule_id))


def counts(repo: str | Path, rules: dict) -> dict[str, int]:
    """Findings per rule id, with every category present (zero when clean)."""
    tally = {rule["rule_id"]: 0 for rule in rules["rules"]}
    for finding in scan_repo(repo, rules):
        tally[finding.rule_id] += 1
    return tally


# ---------------------------------------------------------------------------
# hidden suite
# ---------------------------------------------------------------------------
def run_hidden_tests(task: tasks_mod.Task, repo: Path, timeout_s: int) -> tuple[bool, list[str]]:
    """Run the hidden suite in a child interpreter; never blocks the session."""
    code, failures, n = hidden_mod.run(repo, task.hidden_tests, timeout_s)
    return code == 0 and n > 0, failures


# ---------------------------------------------------------------------------
# baseline / evaluate
# ---------------------------------------------------------------------------
def baseline(task: tasks_mod.Task, rules: dict | None = None) -> dict:
    """The task's starting state: smell counts and hidden-suite outcome."""
    active = rules or load_rules()
    tally = counts(task.repo, active)
    passed, failing = run_hidden_tests(task, task.repo, _timeout())
    return {
        "task_id": task.task_id,
        "counts": dict(tally),
        "debt": debt(tally, active),
        "vuln": vuln(tally, active),
        "tests_pass": passed,
        "n_fail": len(failing),
        "failing_tests": failing,
        "scorer_version": scorer_version(active),
    }


def _timeout() -> int:
    return int(config_mod.load().test_timeout_s)


def _line_delta(before: Path, after: Path) -> tuple[int, int]:
    """Lines added/removed between two repository snapshots (per-file diff)."""
    import difflib

    before_files = _python_files(before)
    after_files = _python_files(after)
    added = removed = 0
    for name in sorted(set(before_files) | set(after_files)):
        old = before_files.get(name, [])
        new = after_files.get(name, [])
        matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "delete"):
                removed += i2 - i1
            if tag in ("replace", "insert"):
                added += j2 - j1
    return added, removed


def evaluate(
    task: tasks_mod.Task,
    repo_after: Path,
    base: dict,
    rules: dict | None = None,
    timeout_s: int | None = None,
    hidden_run: tuple[bool, list[str]] | None = None,
) -> Outcome:
    """After-minus-before metrics plus the hidden-suite verdict.

    ``hidden_run`` lets the caller reuse a suite result it already has; without
    it the suite runs here.
    """
    active = rules or load_rules()
    tally = counts(repo_after, active)
    if hidden_run is None:
        passed, failing = run_hidden_tests(task, repo_after, timeout_s or _timeout())
    else:
        passed, failing = hidden_run
    added, removed = _line_delta(task.repo, repo_after)
    return Outcome(
        tests_pass=passed,
        n_fail=len(failing),
        failing_tests=failing,
        debt_delta=float(debt(tally, active) - int(base["debt"])),
        vuln_delta=vuln(tally, active) - int(base["vuln"]),
        lines_added=added,
        lines_removed=removed,
        scorer_version=scorer_version(active),
    )


def is_correct(before: Outcome | dict, after: Outcome) -> bool:
    """Correct iff the hidden suite improves (fewer failures than before)."""
    before_fail = before["n_fail"] if isinstance(before, dict) else before.n_fail
    return after.n_fail < int(before_fail)


def scored_event(
    suggestion_id: str,
    outcome: Outcome,
    before: Outcome | dict,
    gold_patch_match: bool = False,
) -> dict:
    """The ``suggestion_scored`` payload (schema: :mod:`govern.log`)."""
    return {
        "suggestion_id": suggestion_id,
        "is_correct": is_correct(before, outcome),
        "gold_patch_match": bool(gold_patch_match),
        "scored_by": "hidden_tests",
        "scorer_version": outcome.scorer_version,
    }


# ---------------------------------------------------------------------------
# selftest / CLI
# ---------------------------------------------------------------------------
_SAMPLES = {
    "complexity": ("def f():\n" + "\n".join(f"    v{i} = {i}" for i in range(45)) + "\n    return v0\n",
                   "def f():\n    return 1\n"),
    "duplication": (
        "def a():\n" + "\n".join(f"    v{i} = c({i})" for i in range(6)) + "\n\ndef b():\n"
        + "\n".join(f"    v{i} = c({i})" for i in range(6)) + "\n",
        "def a():\n    return 1\n",
    ),
    "bare_except": ("try:\n    pass\nexcept:\n    pass\n", "try:\n    pass\nexcept ValueError:\n    pass\n"),
    "hardcoded_secret": ('password = "correct-horse-battery"\n', 'password = os.environ["A2_PASSWORD"]\n'),
    "eval_usage": ("v = eval(text)\n", "v = ast.literal_eval(text)\n"),
    "sql_concat": ('q = "SELECT * FROM t WHERE id=" + uid\n', 'q = "SELECT * FROM t WHERE id=?"\n'),
}


def _selftest() -> int:
    rules = load_rules()
    problems: list[str] = []
    for rule_id, (bad, good) in _SAMPLES.items():
        bad_hits = [f for f in scan_source(bad, "bad.py", rules) if f.rule_id == rule_id]
        good_hits = [f for f in scan_source(good, "good.py", rules) if f.rule_id == rule_id]
        if not bad_hits:
            problems.append(f"{rule_id}: no positive fixture hit")
        if good_hits:
            problems.append(f"{rule_id}: negative fixture was flagged")
    tasks = tasks_mod.load_index(ROOT / "corpus")
    from govern import patch as patch_mod

    scratch = _scratch_root() / f"selftest-{os.getpid()}"
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        for task in tasks:
            work = scratch / task.task_id
            shutil.copytree(task.repo, work)
            patch_mod.apply_unified_diff(task.gold_patch.read_text(encoding="utf-8"), work)
            outcome = evaluate(task, work, baseline(task, rules), rules=rules)
            if not outcome.tests_pass:
                problems.append(f"{task.task_id}: gold patch does not pass the hidden suite")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    clean = _scratch_root() / f"clean-{os.getpid()}"
    shutil.rmtree(clean, ignore_errors=True)
    clean.mkdir(parents=True, exist_ok=True)
    try:
        pkg = Path(clean) / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "core.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        tally = counts(clean, rules)
        if debt(tally, rules) != 0:
            problems.append(f"clean repository scores {debt(tally, rules)} debt")
    finally:
        shutil.rmtree(clean, ignore_errors=True)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    names = ", ".join(rule["rule_id"] for rule in rules["rules"])
    print(f"ok: {len(rules['rules'])} rules ({names}) with positive and negative fixtures, "
          f"gold {len(tasks)}/{len(tasks)}, clean repository 0 debt "
          f"({scorer_version(rules)[:24]}...)")
    return 0


def _scratch_root() -> Path:
    root = ROOT / ".scratch"
    root.mkdir(parents=True, exist_ok=True)
    return root


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="score", description="outcome scorer")
    parser.add_argument("--selftest", action="store_true", help="verify the rules and the gold patches")
    parser.add_argument("--task", default=None, help="print the baseline of one task")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.task:
        task = tasks_mod.by_id(tasks_mod.load_index(ROOT / "corpus"), args.task)
        print(json.dumps(baseline(task), indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
