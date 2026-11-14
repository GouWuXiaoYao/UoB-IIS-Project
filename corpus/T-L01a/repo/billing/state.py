"""T-L01a shared process state."""

TAX_RATE = 0.2
PRICE_CACHE = {}


def remember(key, amount):
    PRICE_CACHE[key] = amount
    return amount
