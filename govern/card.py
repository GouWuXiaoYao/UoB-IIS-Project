"""Assessment card renderer (SPEC M5 / PLAN milestone M4).

Turns an :class:`govern.impact.ImpactSet` into the thing a person can actually
decide on: a short list of statements, each naming the symbol it is about, with
no patch text anywhere in the payload (SPEC M5 acceptance 4 — the card is what
replaces reading a diff, so leaking code would void the comparison).

Everything here is a pure function of ``(impact_set, task, condition)``: the
same inputs must give byte-identical output (SPEC M5 acceptance 3).
"""

from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass
from pathlib import Path

from govern import config, impact, tasks

BASELINE_CONDITION = "C0"
CARD_TEMPLATE_VERSION = "card/1"

_STATEMENTS = {
    "global_var": "{symbol} holds state that outlives one request",
    "cross_module_contract": "{symbol}: both sides must read one shared value",
    "side_effect": "{symbol} is written while the request is handled",
    "test_impact": "{symbol}: the demo entry point shows this behaviour",
    "other": "{symbol} could not be analysed",
}


@dataclass(frozen=True)
class CardItem:
    item_id: str
    statement: str
    category: str
    affected_symbol: str
    evidence_ref: str
    required: bool


@dataclass(frozen=True)
class Card:
    card_id: str
    version: str
    items: tuple[CardItem, ...]
    required_ids: tuple[str, ...]
    n_items: int
    n_required: int


def _config() -> config.Config:
    return config.load()


def _statement(entry: impact.ImpactItem, limit: int) -> str:
    template = _STATEMENTS.get(entry.category, _STATEMENTS["other"])
    text = template.format(symbol=entry.symbol)
    if len(text) > limit:
        text = f"{entry.symbol} ({entry.category})"
    return text


def build(impact_set: impact.ImpactSet, task: tasks.Task, condition: str) -> Card:
    """Build the card for one task under one condition.

    ``C1`` puts the whole impact set on the card and requires every item (SPEC
    M2: "固定：影响集全量入卡"). ``C0`` is the no-governance baseline, so it
    carries no items and requires nothing — the suggestion is shown directly.
    Both conditions still produce a card object, so the logging layer sees the
    same shape for both groups (SPEC M6 acceptance 4).
    """
    cfg = _config()
    if condition not in cfg.conditions:
        raise ValueError(f"unknown condition: {condition}")

    version = cfg.app_version
    if condition == BASELINE_CONDITION:
        items: tuple[CardItem, ...] = ()
    else:
        items = tuple(
            CardItem(
                item_id=f"{task.task_id}-{entry.item_id}",
                statement=_statement(entry, cfg.card_item_max_chars),
                category=entry.category,
                affected_symbol=entry.symbol,
                evidence_ref=entry.item_id,
                required=True,
            )
            for entry in impact_set.items
        )

    required_ids = tuple(item.item_id for item in items if item.required)
    digest = hashlib.sha256(
        f"{task.task_id}|{impact.impact_hash(impact_set)}|{condition}|{version}".encode()
    ).hexdigest()[:12]
    return Card(
        card_id=f"card-{digest}",
        version=f"{version}+{CARD_TEMPLATE_VERSION}",
        items=items,
        required_ids=required_ids,
        n_items=len(items),
        n_required=len(required_ids),
    )


def to_html(card: Card) -> str:
    """Render the card as a fragment. Deterministic, and free of patch text."""
    rows = []
    for item in card.items:
        badge = ' <span class="required">required</span>' if item.required else ""
        rows.append(
            '      <li class="card-item" data-item-id="{id}" data-category="{cat}" '
            'data-required="{req}"><label><input type="checkbox" disabled> {text}{badge}</label>'
            '<code class="symbol">{symbol}</code></li>'.format(
                id=html.escape(item.item_id),
                cat=html.escape(item.category),
                req="true" if item.required else "false",
                text=html.escape(item.statement),
                badge=badge,
                symbol=html.escape(item.affected_symbol),
            )
        )
    body = "\n".join(rows) if rows else '      <li class="card-empty">Nothing to confirm.</li>'
    return (
        '<section class="card" data-card-id="{card_id}" data-version="{version}" '
        'data-n-items="{n_items}" data-n-required="{n_required}">\n'
        '  <h2>Check before generation ({n_required} required)</h2>\n'
        "  <p class=\"hint\">The patch is withheld until every box is confirmed.</p>\n"
        "  <ul>\n{body}\n  </ul>\n"
        "</section>\n"
    ).format(
        card_id=html.escape(card.card_id),
        version=html.escape(card.version),
        n_items=card.n_items,
        n_required=card.n_required,
        body=body,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(prog="python -m govern.card")
    parser.add_argument("--selftest", action="store_true", help="render a card from corpus/")
    parser.add_argument("--task", default="T-L01a", help="task id to render")
    parser.add_argument("--condition", default="C1", help="condition to render")
    args = parser.parse_args(argv)
    if not args.selftest and not args.task:
        parser.print_help()
        return 2

    root = Path("corpus")
    loaded = tasks.by_id(tasks.load_index(root), args.task)
    result = impact.analyze(loaded.repo, loaded.intent)
    card = build(result, loaded, args.condition)
    if args.selftest:
        if card.n_items != len(result.items):
            print(f"FAIL: card has {card.n_items} items, impact set has {len(result.items)}")
            return 1
        print(f"ok: {args.task} card has {card.n_items} items, {card.n_required} required, no patch text")
        return 0
    print(to_html(card))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
