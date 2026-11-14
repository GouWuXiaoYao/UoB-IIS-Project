"""Seed-corpus factory (M1).

Generates the pair ``T-L01a`` / ``T-L01b``: two structurally identical legacy
repositories that differ only in domain wording, plus their hidden suites, gold
patches, intents and impact labels. Everything is deterministic: running the
factory twice produces byte-identical output.

Usage:
    python tools/make_repo.py --write     # (re)build corpus/
    python tools/make_repo.py --selftest  # rebuild in memory and compare
"""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from govern import patch  # noqa: E402

CORPUS = ROOT / "corpus"

DOMAINS = (
    {
        "task_id": "T-L01a",
        "pair_id": "PAIR-01",
        "stratum": "L",
        "pkg": "billing",
        "currency": "GBP",
        "cache": "PRICE_CACHE",
        "unit_1": 1249,
        "unit_2": 500,
        "intent": (
            "The checkout team reports that totals no longer reconcile with the ledger. "
            "Move the {pkg} package to integer minor units (cents), stop the module-level "
            "cache from accumulating across calls, and keep the report format the ledger expects."
        ),
    },
    {
        "task_id": "T-L01b",
        "pair_id": "PAIR-01",
        "stratum": "L",
        "pkg": "loans",
        "currency": "GBP",
        "cache": "LOAN_CACHE",
        "unit_1": 1599,
        "unit_2": 450,
        "intent": (
            "The circulation desk reports that fine totals no longer reconcile with the ledger. "
            "Move the {pkg} package to integer minor units (cents), stop the module-level "
            "cache from accumulating across calls, and keep the report format the ledger expects."
        ),
    },
)

STATE_BEFORE = '''"""{task_id} shared process state."""

TAX_RATE = 0.2
{cache} = {{}}


def remember(key, amount):
    {cache}[key] = amount
    return amount
'''

STATE_AFTER = '''"""{task_id} shared process state."""

TAX_PERCENT = 20
'''

CORE_BEFORE = '''from {pkg} import state


def unit_amount(key, base_cents):
    return state.remember(key, base_cents / 100.0)


def total(lines):
    amount = 0.0
    for key, quantity, base_cents in lines:
        amount += unit_amount(key, base_cents) * quantity
    return round(amount * (1 + state.TAX_RATE), 2)


def discounted(lines, percent):
    amount = total(lines)
    return round(amount * (1 - percent / 100.0), 2)
'''

CORE_AFTER = '''from {pkg} import state


def unit_amount(base_cents):
    return int(base_cents)


def total(lines):
    amount = 0
    for _key, quantity, base_cents in lines:
        amount += unit_amount(base_cents) * quantity
    return _with_tax(amount)


def _with_tax(cents):
    return (cents * (100 + state.TAX_PERCENT) + 50) // 100


def discounted(lines, percent):
    amount = total(lines)
    return amount - (amount * percent + 50) // 100
'''

REPORTS_BEFORE = '''from {pkg} import core, state


def summarise(lines):
    amount = core.total(lines)
    return "{currency} {{:.2f}} ({{}} items, tax {{:.0f}}%)".format(
        amount, len(lines), state.TAX_RATE * 100
    )
'''

REPORTS_AFTER = '''from {pkg} import core, state


def summarise(lines):
    cents = core.total(lines)
    return "{currency} {{}}.{{:02d}} ({{}} items, tax {{}}%)".format(
        cents // 100, cents % 100, len(lines), state.TAX_PERCENT
    )
'''

APP = '''from {pkg} import core, reports

DEMO = [("K-1", 2, {unit_1}), ("K-2", 1, {unit_2})]


def main():
    print("demo total:", core.total(DEMO))
    print("demo report:", reports.summarise(DEMO))


if __name__ == "__main__":
    main()
'''

HIDDEN = '''"""Hidden acceptance suite for {task_id}."""

from {pkg} import core, reports, state

DEMO = [("K-1", 2, {unit_1}), ("K-2", 1, {unit_2})]
BASE_CENTS = {unit_1} * 2 + {unit_2}
EXPECTED_CENTS = (BASE_CENTS * 120 + 50) // 100


def test_total_is_integer_minor_units():
    value = core.total(DEMO)
    assert isinstance(value, int), "total must return integer minor units, got " + type(value).__name__
    assert value == EXPECTED_CENTS, "unexpected total: %r" % (value,)


def test_total_does_not_accumulate_global_state():
    core.total(DEMO)
    core.total(DEMO)
    cache = getattr(state, "{cache}", {{}})
    assert cache == {{}}, "module-level cache grew to %d entries" % len(cache)


def test_report_uses_the_minor_unit_contract():
    text = reports.summarise(DEMO)
    expected = "{currency} {{}}.{{:02d}} (2 items, tax 20%)".format(
        EXPECTED_CENTS // 100, EXPECTED_CENTS % 100
    )
    assert text == expected, "report drifted: %r" % (text,)
'''

INTENT = """# Intent — {task_id}

{intent}

## Scope

- Package: `{pkg}/`
- Entry point: `python app.py`
- Acceptance is decided by an unseen test suite; make the public behaviour
  described above true without changing the demo scenario in `app.py`.
"""


def _render(template: str, domain: dict) -> str:
    text = template.format(**domain)
    return text.replace("{pkg}", domain["pkg"]).replace("{currency}", domain["currency"])


def _files(domain: dict, after: bool) -> dict[str, str]:
    pkg = domain["pkg"]
    return {
        f"{pkg}/__init__.py": f'"""{pkg} package."""\n',
        f"{pkg}/state.py": _render(STATE_AFTER if after else STATE_BEFORE, domain),
        f"{pkg}/core.py": _render(CORE_AFTER if after else CORE_BEFORE, domain),
        f"{pkg}/reports.py": _render(REPORTS_AFTER if after else REPORTS_BEFORE, domain),
        "app.py": _render(APP, domain),
    }


def _diff(domain: dict) -> str:
    before, after = _files(domain, after=False), _files(domain, after=True)
    chunks = []
    for name in sorted(before):
        if before[name] == after[name]:
            continue
        chunks.append(
            "".join(
                difflib.unified_diff(
                    before[name].splitlines(keepends=True),
                    after[name].splitlines(keepends=True),
                    fromfile=f"a/{name}",
                    tofile=f"b/{name}",
                )
            )
        )
    return "".join(chunks)


def _labels(domain: dict) -> dict:
    pkg = domain["pkg"]
    total_cents = domain["unit_1"] * 2 + domain["unit_2"]
    return {
        "task_id": domain["task_id"],
        "files_to_change": 3,
        "functions_to_change": 3,
        "hidden_tests": 3,
        "global_vars": [
            {
                "symbol": f"{pkg}.state.{domain['cache']}",
                "file": f"{pkg}/state.py",
                "kind": "mutable_global",
                "note": "must stop being written during total()",
            }
        ],
        "cross_module_contracts": [
            {
                "contract": (
                    f"{pkg}.core.total returns integer minor units and "
                    f"{pkg}.reports.summarise formats them without re-deriving tax"
                ),
                "producer": f"{pkg}/core.py",
                "consumer": f"{pkg}/reports.py",
                "baseline_minor_units": total_cents,
            }
        ],
        "untouched": ["app.py"],
    }


def build_corpus() -> dict[str, dict[str, str]]:
    """Return {relative path: file content} for the whole corpus."""
    out: dict[str, dict[str, str]] = {}
    index = []
    for domain in DOMAINS:
        base = f"{domain['task_id']}"
        files: dict[str, str] = {}
        for name, text in _files(domain, after=False).items():
            files[f"{base}/repo/{name}"] = text
        files[f"{base}/gold.patch"] = _diff(domain)
        files[f"{base}/tests_hidden/test_{domain['pkg']}.py"] = _render(HIDDEN, domain)
        files[f"{base}/intent.md"] = INTENT.format(**domain)
        files[f"{base}/impact_labels.json"] = json.dumps(_labels(domain), indent=2) + "\n"
        out.update(files)
        index.append(
            {
                "task_id": domain["task_id"],
                "pair_id": domain["pair_id"],
                "stratum": domain["stratum"],
                "intent": domain["intent"].format(**domain),
                "labels": {
                    "files_to_change": 3,
                    "functions_to_change": 3,
                    "hidden_tests": 3,
                },
            }
        )
    out["index.json"] = json.dumps({"tasks": index}, indent=2) + "\n"
    return out


def write_corpus() -> None:
    files = build_corpus()
    for name in sorted(files):
        path = CORPUS / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[name], encoding="utf-8", newline="")
    # Drop the corpus tree of any task that no longer exists.
    known = {d["task_id"] for d in DOMAINS}
    for child in CORPUS.iterdir():
        if child.is_dir() and child.name not in known:
            shutil.rmtree(child)
    for domain in DOMAINS:
        text = (CORPUS / domain["task_id"] / "gold.patch").read_text(encoding="utf-8")
        patch.parse(text)  # fail fast: every generated patch must be applicable


def selftest() -> int:
    files = build_corpus()
    mismatched = []
    for name, text in files.items():
        path = CORPUS / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            mismatched.append(name)
    if mismatched:
        print("drift:", ", ".join(sorted(mismatched)))
        return 1
    print(f"ok: {len(files)} corpus files match the factory")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python tools/make_repo.py")
    parser.add_argument("--write", action="store_true", help="write corpus/ from the templates")
    parser.add_argument("--selftest", action="store_true", help="verify corpus/ matches templates")
    args = parser.parse_args(argv)
    if args.write:
        write_corpus()
        print("wrote corpus/ for", ", ".join(d["task_id"] for d in DOMAINS))
        return 0
    if args.selftest:
        return selftest()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
