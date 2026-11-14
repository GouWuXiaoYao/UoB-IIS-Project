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
    {
        "task_id": "T-L02a",
        "pair_id": "PAIR-02",
        "stratum": "M",
        "pkg": "ticketing",
        "currency": "GBP",
        "cache": "TICKET_CACHE",
        "unit_1": 1899,
        "unit_2": 725,
        "intent": (
            "Support reports that box-office totals disagree with the finance export. "
            "Move the {pkg} package to integer minor units (cents), stop the module-level "
            "cache from accumulating across calls, and make the report and the CSV export "
            "agree with the same money contract."
        ),
    },
    {
        "task_id": "T-L02b",
        "pair_id": "PAIR-02",
        "stratum": "M",
        "pkg": "payroll",
        "currency": "GBP",
        "cache": "PAYROLL_CACHE",
        "unit_1": 2050,
        "unit_2": 640,
        "intent": (
            "Finance reports that payslip totals disagree with the ledger export. "
            "Move the {pkg} package to integer minor units (cents), stop the module-level "
            "cache from accumulating across calls, and make the report and the CSV export "
            "agree with the same money contract."
        ),
    },
    {
        "task_id": "T-L03a",
        "pair_id": "PAIR-03",
        "stratum": "H",
        "pkg": "inventory",
        "currency": "GBP",
        "cache": "STOCK_CACHE",
        "unit_1": 2349,
        "unit_2": 1205,
        "intent": (
            "Warehouse auditors found stock totals that drift between the report, the CSV export "
            "and the audit trail. Move the {pkg} package to integer minor units (cents), remove "
            "the process-wide caches and the ledger that grows across calls, stop evaluating "
            "discount expressions with eval, and make every consumer agree with one money contract."
        ),
    },
    {
        "task_id": "T-L03b",
        "pair_id": "PAIR-03",
        "stratum": "H",
        "pkg": "fleet",
        "currency": "GBP",
        "cache": "FLEET_CACHE",
        "unit_1": 2580,
        "unit_2": 980,
        "intent": (
            "Depot auditors found mileage totals that drift between the report, the CSV export "
            "and the audit trail. Move the {pkg} package to integer minor units (cents), remove "
            "the process-wide caches and the ledger that grows across calls, stop evaluating "
            "discount expressions with eval, and make every consumer agree with one money contract."
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


# --- strata M and H ---------------------------------------------------------
# These templates use __TOKEN__ placeholders instead of str.format braces: the
# legacy code contains dict/set literals and percent formatting, and doubling
# every brace to survive .format() is a reliable way to introduce typos.

M_STATE_BEFORE = '''"""__TASK__ shared process state."""

TAX_RATE = 0.2
__CACHE__ = {}


def remember(key, amount):
    __CACHE__[key] = amount
    return amount
'''

M_STATE_AFTER = '''"""__TASK__ shared process state."""

TAX_PERCENT = 20
'''

M_CORE_BEFORE = '''from __PKG__ import state


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

M_CORE_AFTER = '''from __PKG__ import state


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
    return amount - (amount * int(percent) + 50) // 100
'''

M_REPORTS_BEFORE = '''from __PKG__ import state


def _recompute(lines):
    subtotal = 0.0
    for _key, quantity, base_cents in lines:
        subtotal += base_cents / 100.0 * quantity
    return round(subtotal * (1 + state.TAX_RATE), 2)


def summarise(lines):
    try:
        amount = _recompute(lines)
    except:
        amount = 0.0
    return "__CURRENCY__ {:.2f} ({} items, tax {:.0f}%)".format(
        amount, len(lines), state.TAX_RATE * 100
    )
'''

REPORTS_MINOR_AFTER = '''from __PKG__ import core, state


def summarise(lines):
    cents = core.total(lines)
    return "__CURRENCY__ {}.{:02d} ({} items, tax {}%)".format(
        cents // 100, cents % 100, len(lines), state.TAX_PERCENT
    )
'''

M_EXPORT_BEFORE = '''from __PKG__ import core, state


def rows(lines):
    out = ["key,amount"]
    for key, quantity, base_cents in lines:
        unit = round(base_cents / 100.0 * (1 + state.TAX_RATE), 2)
        out.append("%s,%.2f" % (key, unit * quantity))
    return "\\n".join(out) + "\\n"


def total_cents(lines):
    return int(core.total(lines) * 100)
'''

EXPORT_MINOR_AFTER = '''from __PKG__ import core


def rows(lines):
    out = ["key,amount_cents"]
    for key, quantity, base_cents in lines:
        out.append("%s,%d" % (key, core.unit_amount(base_cents) * quantity))
    return "\\n".join(out) + "\\n"


def total_cents(lines):
    return core.total(lines)
'''

H_STATE_BEFORE = '''"""__TASK__ shared process state."""

TAX_RATE = 0.2
__CACHE__ = {}
LEDGER = []


def remember(key, amount, ledger=LEDGER):
    __CACHE__[key] = amount
    ledger.append(key)
    return amount
'''

H_CORE_BEFORE = '''from __PKG__ import state


def unit_amount(key, base_cents):
    return state.remember(key, base_cents / 100.0)


def total(lines):
    amount = 0.0
    for key, quantity, base_cents in lines:
        amount += unit_amount(key, base_cents) * quantity
    return round(amount * (1 + state.TAX_RATE), 2)


def discounted(lines, expression):
    amount = total(lines)
    percent = eval(expression)
    return round(amount * (1 - percent / 100.0), 2)
'''

H_CORE_AFTER = '''from __PKG__ import state


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
    rate = int(str(percent))
    if rate < 0 or rate > 100:
        raise ValueError("discount percent out of range")
    return amount - (amount * rate + 50) // 100
'''

H_AUDIT_BEFORE = '''from __PKG__ import state


def gross_cents(base_cents, quantity):
    return int(base_cents / 100.0 * quantity * 100)


def with_tax(cents):
    return int(cents / 100.0 * (1 + state.TAX_RATE) * 100)
'''

H_AUDIT_AFTER = '''from __PKG__ import state


def gross_cents(base_cents, quantity):
    return int(base_cents) * quantity


def with_tax(cents):
    return (cents * (100 + state.TAX_PERCENT) + 50) // 100
'''

HIDDEN_M = '''"""Hidden acceptance suite for __TASK__."""

from __PKG__ import core, export, reports, state

DEMO = [("K-1", 2, __UNIT1__), ("K-2", 1, __UNIT2__)]
BASE_CENTS = __UNIT1__ * 2 + __UNIT2__
EXPECTED_CENTS = (BASE_CENTS * 120 + 50) // 100


def test_total_is_integer_minor_units():
    value = core.total(DEMO)
    assert isinstance(value, int), "total must return integer minor units, got " + type(value).__name__
    assert value == EXPECTED_CENTS, "unexpected total: %r" % (value,)


def test_total_does_not_accumulate_global_state():
    core.total(DEMO)
    core.total(DEMO)
    cache = getattr(state, "__CACHE__", {})
    assert cache == {}, "module-level cache grew to %d entries" % len(cache)


def test_report_uses_the_minor_unit_contract():
    text = reports.summarise(DEMO)
    expected = "__CURRENCY__ {}.{:02d} (2 items, tax 20%)".format(
        EXPECTED_CENTS // 100, EXPECTED_CENTS % 100
    )
    assert text == expected, "report drifted: %r" % (text,)


def test_export_agrees_with_the_minor_unit_contract():
    expected = "key,amount_cents\\nK-1,%d\\nK-2,%d\\n" % (__UNIT1__ * 2, __UNIT2__)
    assert export.rows(DEMO) == expected, "export drifted: %r" % (export.rows(DEMO),)
    assert export.total_cents(DEMO) == EXPECTED_CENTS
'''

HIDDEN_H = '''"""Hidden acceptance suite for __TASK__."""

from __PKG__ import audit, core, export, reports, state

DEMO = [("K-1", 2, __UNIT1__), ("K-2", 1, __UNIT2__)]
BASE_CENTS = __UNIT1__ * 2 + __UNIT2__
EXPECTED_CENTS = (BASE_CENTS * 120 + 50) // 100


def test_total_is_integer_minor_units():
    value = core.total(DEMO)
    assert isinstance(value, int), "total must return integer minor units, got " + type(value).__name__
    assert value == EXPECTED_CENTS, "unexpected total: %r" % (value,)


def test_total_does_not_accumulate_global_state():
    core.total(DEMO)
    core.total(DEMO)
    cache = getattr(state, "__CACHE__", {})
    assert cache == {}, "module-level cache grew to %d entries" % len(cache)
    ledger = getattr(state, "LEDGER", [])
    assert ledger == [], "module-level ledger grew to %d entries" % len(ledger)


def test_report_uses_the_minor_unit_contract():
    text = reports.summarise(DEMO)
    expected = "__CURRENCY__ {}.{:02d} (2 items, tax 20%)".format(
        EXPECTED_CENTS // 100, EXPECTED_CENTS % 100
    )
    assert text == expected, "report drifted: %r" % (text,)


def test_export_agrees_with_the_minor_unit_contract():
    expected = "key,amount_cents\\nK-1,%d\\nK-2,%d\\n" % (__UNIT1__ * 2, __UNIT2__)
    assert export.rows(DEMO) == expected, "export drifted: %r" % (export.rows(DEMO),)
    assert export.total_cents(DEMO) == EXPECTED_CENTS


def test_audit_agrees_with_the_money_contract():
    cents = sum(audit.gross_cents(base, quantity) for _key, quantity, base in DEMO)
    assert cents == BASE_CENTS, "audit subtotal drifted: %r" % (cents,)
    assert audit.with_tax(cents) == core.total(DEMO), "audit total drifted: %r" % (audit.with_tax(cents),)


def test_discount_is_not_an_expression():
    value = core.discounted(DEMO, "10")
    assert isinstance(value, int), "discounted must return integer minor units"
    assert core.discounted(DEMO, "0") == core.total(DEMO), "a zero discount must be a no-op"
    try:
        core.discounted(DEMO, "__import__('os').getcwd()")
    except (ValueError, TypeError):
        pass
    else:
        raise AssertionError("discount must reject non-numeric expressions")
'''


def _fill(template: str, domain: dict) -> str:
    tokens = {
        "__TASK__": domain["task_id"],
        "__PKG__": domain["pkg"],
        "__CACHE__": domain["cache"],
        "__CURRENCY__": domain["currency"],
        "__UNIT1__": str(domain["unit_1"]),
        "__UNIT2__": str(domain["unit_2"]),
    }
    text = template
    for token, value in tokens.items():
        text = text.replace(token, value)
    return text


def _files(domain: dict, after: bool) -> dict[str, str]:
    pkg = domain["pkg"]
    stratum = domain["stratum"]
    common = {
        f"{pkg}/__init__.py": f'"""{pkg} package."""\n',
        "app.py": _render(APP, domain),
    }
    if stratum == "L":
        return {
            **common,
            f"{pkg}/state.py": _render(STATE_AFTER if after else STATE_BEFORE, domain),
            f"{pkg}/core.py": _render(CORE_AFTER if after else CORE_BEFORE, domain),
            f"{pkg}/reports.py": _render(REPORTS_AFTER if after else REPORTS_BEFORE, domain),
        }
    if stratum == "M":
        return {
            **common,
            f"{pkg}/state.py": _fill(M_STATE_AFTER if after else M_STATE_BEFORE, domain),
            f"{pkg}/core.py": _fill(M_CORE_AFTER if after else M_CORE_BEFORE, domain),
            f"{pkg}/reports.py": _fill(REPORTS_MINOR_AFTER if after else M_REPORTS_BEFORE, domain),
            f"{pkg}/export.py": _fill(EXPORT_MINOR_AFTER if after else M_EXPORT_BEFORE, domain),
        }
    return {
        **common,
        f"{pkg}/state.py": _fill(M_STATE_AFTER if after else H_STATE_BEFORE, domain),
        f"{pkg}/core.py": _fill(H_CORE_AFTER if after else H_CORE_BEFORE, domain),
        f"{pkg}/reports.py": _fill(REPORTS_MINOR_AFTER if after else M_REPORTS_BEFORE, domain),
        f"{pkg}/export.py": _fill(EXPORT_MINOR_AFTER if after else M_EXPORT_BEFORE, domain),
        f"{pkg}/audit.py": _fill(H_AUDIT_AFTER if after else H_AUDIT_BEFORE, domain),
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


STRATUM_SHAPE = {
    "L": {"functions_to_change": 3, "extra_globals": (), "extra_consumers": ()},
    "M": {
        "functions_to_change": 4,
        "extra_globals": (),
        "extra_consumers": (("export", "csv export must consume the same minor-unit contract"),),
    },
    "H": {
        "functions_to_change": 5,
        "extra_globals": (("LEDGER", "mutable list used as a default argument; must not grow"),),
        "extra_consumers": (
            ("export", "csv export must consume the same minor-unit contract"),
            ("audit", "audit trail must derive tax with the same integer rounding"),
        ),
    },
}


def _hidden_for(domain: dict) -> str:
    stratum = domain["stratum"]
    if stratum == "L":
        return _render(HIDDEN, domain)
    return _fill(HIDDEN_M if stratum == "M" else HIDDEN_H, domain)


def _labels(domain: dict, diff: str) -> dict:
    pkg = domain["pkg"]
    shape = STRATUM_SHAPE[domain["stratum"]]
    total_cents = domain["unit_1"] * 2 + domain["unit_2"]
    globals_ = [
        {
            "symbol": f"{pkg}.state.{domain['cache']}",
            "file": f"{pkg}/state.py",
            "kind": "mutable_global",
            "note": "must stop being written during total()",
        }
    ]
    for name, note in shape["extra_globals"]:
        globals_.append(
            {
                "symbol": f"{pkg}.state.{name}",
                "file": f"{pkg}/state.py",
                "kind": "mutable_global",
                "note": note,
            }
        )
    contracts = [
        {
            "contract": (
                f"{pkg}.core.total returns integer minor units and "
                f"{pkg}.reports.summarise formats them without re-deriving tax"
            ),
            "producer": f"{pkg}/core.py",
            "consumer": f"{pkg}/reports.py",
            "baseline_minor_units": total_cents,
        }
    ]
    for module, contract in shape["extra_consumers"]:
        contracts.append(
            {
                "contract": contract,
                "producer": f"{pkg}/core.py",
                "consumer": f"{pkg}/{module}.py",
                "baseline_minor_units": total_cents,
            }
        )
    return {
        "task_id": domain["task_id"],
        "pair_id": domain["pair_id"],
        "stratum": domain["stratum"],
        "files_to_change": len(patch.changed_files(diff)),
        "functions_to_change": shape["functions_to_change"],
        "hidden_tests": _hidden_for(domain).count("\ndef test_"),
        "global_vars": globals_,
        "cross_module_contracts": contracts,
        "untouched": ["app.py"],
    }


def build_corpus() -> dict[str, dict[str, str]]:
    """Return {relative path: file content} for the whole corpus."""
    out: dict[str, dict[str, str]] = {}
    index = []
    for domain in DOMAINS:
        base = f"{domain['task_id']}"
        diff = _diff(domain)
        labels = _labels(domain, diff)
        files: dict[str, str] = {}
        for name, text in _files(domain, after=False).items():
            files[f"{base}/repo/{name}"] = text
        files[f"{base}/gold.patch"] = diff
        files[f"{base}/tests_hidden/test_{domain['pkg']}.py"] = _hidden_for(domain)
        files[f"{base}/intent.md"] = INTENT.format(**domain)
        files[f"{base}/impact_labels.json"] = json.dumps(labels, indent=2) + "\n"
        out.update(files)
        index.append(
            {
                "task_id": domain["task_id"],
                "pair_id": domain["pair_id"],
                "stratum": domain["stratum"],
                "intent": domain["intent"].format(**domain),
                "labels": {
                    "files_to_change": labels["files_to_change"],
                    "functions_to_change": labels["functions_to_change"],
                    "hidden_tests": labels["hidden_tests"],
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
