"""T-L01b shared process state."""

TAX_RATE = 0.2
LOAN_CACHE = {}


def remember(key, amount):
    LOAN_CACHE[key] = amount
    return amount
