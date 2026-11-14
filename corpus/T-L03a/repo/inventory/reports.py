from inventory import state


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
    return "GBP {:.2f} ({} items, tax {:.0f}%)".format(
        amount, len(lines), state.TAX_RATE * 100
    )
