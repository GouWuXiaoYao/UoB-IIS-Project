"""T-L02a shared process state."""

TAX_RATE = 0.2
TICKET_CACHE = {}


def remember(key, amount):
    TICKET_CACHE[key] = amount
    return amount
