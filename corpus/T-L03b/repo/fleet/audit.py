from fleet import state


def gross_cents(base_cents, quantity):
    return int(base_cents / 100.0 * quantity * 100)


def with_tax(cents):
    return int(cents / 100.0 * (1 + state.TAX_RATE) * 100)
