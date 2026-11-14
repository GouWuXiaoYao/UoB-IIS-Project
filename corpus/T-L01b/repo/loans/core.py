from loans import state


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
