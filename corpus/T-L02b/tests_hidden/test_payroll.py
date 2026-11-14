"""Hidden acceptance suite for T-L02b."""

from payroll import core, export, reports, state

DEMO = [("K-1", 2, 2050), ("K-2", 1, 640)]
BASE_CENTS = 2050 * 2 + 640
EXPECTED_CENTS = (BASE_CENTS * 120 + 50) // 100


def test_total_is_integer_minor_units():
    value = core.total(DEMO)
    assert isinstance(value, int), "total must return integer minor units, got " + type(value).__name__
    assert value == EXPECTED_CENTS, "unexpected total: %r" % (value,)


def test_total_does_not_accumulate_global_state():
    core.total(DEMO)
    core.total(DEMO)
    cache = getattr(state, "PAYROLL_CACHE", {})
    assert cache == {}, "module-level cache grew to %d entries" % len(cache)


def test_report_uses_the_minor_unit_contract():
    text = reports.summarise(DEMO)
    expected = "GBP {}.{:02d} (2 items, tax 20%)".format(
        EXPECTED_CENTS // 100, EXPECTED_CENTS % 100
    )
    assert text == expected, "report drifted: %r" % (text,)


def test_export_agrees_with_the_minor_unit_contract():
    expected = "key,amount_cents\nK-1,%d\nK-2,%d\n" % (2050 * 2, 640)
    assert export.rows(DEMO) == expected, "export drifted: %r" % (export.rows(DEMO),)
    assert export.total_cents(DEMO) == EXPECTED_CENTS
