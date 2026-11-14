"""Constraint and impact analyser (M3 / SPEC M4).

Pure ``ast`` work: given a repository snapshot it reports

* module-level mutable globals (``global_var``),
* cross-module contracts — a value that two or more package modules read and
  therefore must agree on (``cross_module_contract``),
* functions that write those globals (``side_effect``),
* demo entry points that exercise a package module (``test_impact``),
* anything the analyser could not read (``other``, e.g. a syntax error).

Operational definition of a contract, since it drives recall: a *contract* is a
top-level **value** of module ``T`` (not a function) that is read by at least two
package modules. The anchor is the reader that the other readers call into, so
``core.total`` ↔ ``reports``/``export``/``audit`` collapses onto one producer.
Reading a function is an API call, not a shared assumption, so it does not count.

``intent`` is accepted because PLAN fixes the signature. The analysis is
deliberately intent-independent: the same repository must yield the same set for
the same snapshot, whatever the task wording (see ``tests/test_impact.py``).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from govern import config, tasks

CATEGORIES = ("global_var", "cross_module_contract", "side_effect", "test_impact", "other")
MUTABLE_NODES = (ast.Dict, ast.List, ast.Set)
MUTABLE_CALLS = {"dict", "list", "set", "defaultdict", "OrderedDict"}
CORPUS_ROOT = Path("corpus")


@dataclass(frozen=True)
class ImpactItem:
    item_id: str
    category: str
    symbol: str
    files: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class ImpactSet:
    items: tuple[ImpactItem, ...] = ()

    def of(self, category: str) -> tuple[ImpactItem, ...]:
        return tuple(item for item in self.items if item.category == category)


@dataclass
class _Module:
    name: str
    path: Path
    rel: str
    is_package: bool
    tree: ast.Module
    values: set[str] = field(default_factory=set)
    functions: set[str] = field(default_factory=set)
    mutables: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    calls: set[str] = field(default_factory=set)
    reads: set[tuple[str, str]] = field(default_factory=set)
    side_effects: set[tuple[str, str]] = field(default_factory=set)


def _module_name(rel: str) -> str:
    return rel.replace("\\", "/")[: -len(".py")].replace("/", ".")


def _is_mutable(node: ast.expr) -> str:
    if isinstance(node, MUTABLE_NODES):
        return "mutable literal"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in MUTABLE_CALLS:
        return f"mutable {node.func.id}()"
    return ""


def _collect(module: _Module) -> None:
    for node in module.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module.functions.add(node.name)
            module.values.add(node.name)
        elif isinstance(node, ast.ClassDef):
            module.values.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module.values.add(target.id)
                    kind = _is_mutable(node.value)
                    if kind:
                        module.mutables[target.id] = kind
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            module.values.add(node.target.id)
            if node.value is not None and _is_mutable(node.value):
                module.mutables[node.target.id] = _is_mutable(node.value)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                module.aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module.aliases[alias.asname or alias.name.split(".")[0]] = alias.name


def _walk_usage(module: _Module) -> None:
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base = node.func.value
            if isinstance(base, ast.Name) and base.id in module.aliases:
                module.calls.add(f"{module.aliases[base.id]}|{node.func.attr}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            target = module.aliases.get(node.value.id)
            if target:
                module.reads.add((target, node.attr))
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.Delete)):
            targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target]
            for target in targets:
                name = target.value if isinstance(target, (ast.Subscript, ast.Attribute)) else None
                if isinstance(name, ast.Name) and name.id in module.mutables:
                    module.side_effects.add((_enclosing_function(node), name.id))


def _enclosing_function(node: ast.stmt) -> str:
    """Owner function of a statement, set by :func:`_annotate_owners`."""
    return getattr(node, "_owner", "<module>")


def _annotate_owners(module: _Module) -> None:
    for node in module.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if isinstance(child, ast.stmt):
                    child._owner = node.name  # type: ignore[attr-defined]


def _load(repo: Path) -> tuple[list[_Module], list[ImpactItem]]:
    modules: list[_Module] = []
    broken: list[ImpactItem] = []
    for path in sorted(p for p in repo.rglob("*.py") if "__pycache__" not in p.parts):
        rel = path.relative_to(repo).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            detail = f"syntax error in {rel}: {type(exc).__name__}"
            broken.append(
                ImpactItem("", "other", f"unparsed:{rel}", (rel,), detail)
            )
            continue
        module = _Module(
            name=_module_name(rel),
            path=path,
            rel=rel,
            is_package="/" in rel,
            tree=tree,
        )
        _collect(module)
        _annotate_owners(module)
        _walk_usage(module)
        modules.append(module)
    return modules, broken


def analyze(repo: str | Path, intent: str) -> ImpactSet:
    """Return the impact set for a repository snapshot."""
    del intent  # see the module docstring: the analysis must be wording-independent
    root = Path(repo)
    if not root.is_dir():
        return ImpactSet(
            (ImpactItem("", "other", f"missing:{root.name}", (), f"repository not found: {root}"),)
        )

    modules, items = _load(root)
    by_name = {m.name: m for m in modules}
    packages = [m for m in modules if m.is_package]
    values = {m.name: m.values for m in packages}

    for module in packages:
        for name, kind in sorted(module.mutables.items()):
            items.append(
                ImpactItem(
                    "",
                    "global_var",
                    f"{module.name}.{name}",
                    (module.rel,),
                    f"module-level {kind} {name}; it outlives a single call",
                )
            )
        for owner, name in sorted(module.side_effects):
            items.append(
                ImpactItem(
                    "",
                    "side_effect",
                    f"{module.name}.{owner}->{name}",
                    (module.rel,),
                    f"{owner}() writes the module-level {name}",
                )
            )

    readers: dict[tuple[str, str], set[str]] = {}
    for module in packages:
        for target, attr in module.reads:
            if target in by_name and attr in values.get(target, set()):
                if attr in by_name[target].functions:
                    continue  # calling an API is not a shared assumption
                readers.setdefault((target, attr), set()).add(module.name)

    calls_from: dict[str, set[str]] = {m.name: set() for m in packages}
    for module in packages:
        for edge in module.calls:
            target, attr = edge.split("|", 1)
            if target in by_name and attr in by_name[target].functions:
                calls_from[module.name].add(target)

    for (target, attr), group in sorted(readers.items()):
        if len(group) < 2:
            continue
        anchor = sorted(group, key=lambda name: (-len([c for c in calls_from if name in calls_from[c]]), name))
        producer = anchor[0]
        for consumer in sorted(group - {producer}):
            items.append(
                ImpactItem(
                    "",
                    "cross_module_contract",
                    f"{producer}->{consumer}",
                    (by_name[producer].rel, by_name[consumer].rel),
                    f"both read {target}.{attr}; the value must stay consistent across modules",
                )
            )

    for module in modules:
        if module.is_package:
            continue
        for alias, target in sorted(module.aliases.items()):
            if target in by_name and by_name[target].is_package:
                items.append(
                    ImpactItem(
                        "",
                        "test_impact",
                        f"{module.name}->{target}",
                        (module.rel, by_name[target].rel),
                        f"demo entry point {module.rel} exercises {target}",
                    )
                )

    unique: dict[tuple[str, str, tuple[str, ...], str], ImpactItem] = {}
    for item in items:
        unique[(item.category, item.symbol, item.files, item.detail)] = item
    ordered = sorted(
        unique.values(), key=lambda i: (i.category, i.symbol, i.files, i.detail)
    )
    identified = tuple(
        ImpactItem(f"{item.category}-{index:03d}", item.category, item.symbol, item.files, item.detail)
        for index, item in enumerate(ordered, start=1)
    )
    return ImpactSet(identified)


def impact_hash(result: ImpactSet) -> str:
    digest = hashlib.sha256()
    for item in result.items:
        digest.update(f"{item.category}|{item.symbol}|{','.join(item.files)}|{item.detail}\n".encode())
    return "sha256:" + digest.hexdigest()


def risk_level(result: ImpactSet) -> str:
    if result.of("cross_module_contract"):
        return "high"
    if result.of("global_var") or result.of("side_effect"):
        return "medium"
    return "low"


def _module_of(path: str) -> str:
    return path.replace("\\", "/")[: -len(".py")].replace("/", ".")


def recall_precision(result: ImpactSet, labels: dict) -> tuple[float, float]:
    """Recall and precision over the labelled categories (globals + contracts).

    SPEC M4 acceptance 1 and assumption A-9 define the denominator: the labels
    list the globals and contracts a human says matter. Advisory categories
    (``side_effect``, ``test_impact``, ``other``) are not scored, because the
    labels were never meant to enumerate them.
    """
    expected = {g["symbol"] for g in labels.get("global_vars", [])}
    expected |= {
        f"{_module_of(c['producer'])}->{_module_of(c['consumer'])}"
        for c in labels.get("cross_module_contracts", [])
    }
    found = {i.symbol for i in result.of("global_var")}
    found |= {i.symbol for i in result.of("cross_module_contract")}

    hits = len(expected & found)
    recall = 1.0 if not expected else hits / len(expected)
    precision = 1.0 if not found else hits / len(found)
    return recall, precision


def _selftest() -> int:
    cfg = config.load()
    loaded = tasks.load_index(CORPUS_ROOT)
    if not loaded:
        print("no tasks in corpus/", file=sys.stderr)
        return 1
    worst_recall, worst_precision = 1.0, 1.0
    for task in loaded:
        labels = json.loads((CORPUS_ROOT / task.task_id / "impact_labels.json").read_text(encoding="utf-8"))
        result = analyze(task.repo, task.intent)
        recall, precision = recall_precision(result, labels)
        worst_recall = min(worst_recall, recall)
        worst_precision = min(worst_precision, precision)
        print(f"  {task.task_id}: recall={recall:.2f} precision={precision:.2f} risk={risk_level(result)}")
    ok = worst_recall >= cfg.impact_recall_min and worst_precision >= cfg.impact_precision_min
    status = "ok" if ok else "FAIL"
    print(
        f"{status}: recall={worst_recall:.2f} precision={worst_precision:.2f} on {len(loaded)} tasks "
        f"(min recall {cfg.impact_recall_min:.2f}, min precision {cfg.impact_precision_min:.2f})"
    )
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m govern.impact")
    parser.add_argument("--selftest", action="store_true", help="score the analyser on corpus/")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
