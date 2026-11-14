"""T-L03b shared process state."""

TAX_RATE = 0.2
FLEET_CACHE = {}
LEDGER = []


def remember(key, amount, ledger=LEDGER):
    FLEET_CACHE[key] = amount
    ledger.append(key)
    return amount
