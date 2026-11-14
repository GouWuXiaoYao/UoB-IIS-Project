"""T-L02b shared process state."""

TAX_RATE = 0.2
PAYROLL_CACHE = {}


def remember(key, amount):
    PAYROLL_CACHE[key] = amount
    return amount
