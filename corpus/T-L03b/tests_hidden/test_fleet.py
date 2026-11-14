"""Hidden acceptance suite for T-L03b."""

from fleet import audit, core, export, reports, state

DEMO = [("K-1", 2, 2580), ("K-2", 1, 980)]
BASE_CENTS = 2580 * 2 + 980
EXPECTED_CENTS = (BASE_CENTS * 120 + 50) // 100


def test_total_is_integer_minor_units():
    value = core.total(DEMO)
    assert isinstance(value, int), "total must return integer minor units, got " + type(value).__name__
    assert value == EXPECTED_CENTS, "unexpected total: %r" % (value,)


def test_total_does_not_accumulate_global_state():
    core.total(DEMO)
    core.total(DEMO)
    cache = getattr(state, "FLEET_CACHE", {})
    assert cache == {}, "module-level cache grew to %d entries" % len(cache)
    ledger = getattr(state, "LEDGER", [])
    assert ledger == [], "module-level ledger grew to %d entries" % len(ledger)


def test_report_uses_the_minor_unit_contract():
    text = reports.summarise(DEMO)
    expected = "GBP {}.{:02d} (2 items, tax 20%)".format(
        EXPECTED_CENTS // 100, EXPECTED_CENTS % 100
    )
    assert text == expected, "report drifted: %r" % (text,)


def test_export_agrees_with_the_minor_unit_contract():
    expected = "key,amount_cents\nK-1,%d\nK-2,%d\n" % (2580 * 2, 980)
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
