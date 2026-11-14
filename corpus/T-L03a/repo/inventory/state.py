"""T-L03a shared process state."""

TAX_RATE = 0.2
STOCK_CACHE = {}
LEDGER = []


def remember(key, amount, ledger=LEDGER):
    STOCK_CACHE[key] = amount
    ledger.append(key)
    return amount
