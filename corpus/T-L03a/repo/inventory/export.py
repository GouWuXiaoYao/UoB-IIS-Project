from inventory import core, state


def rows(lines):
    out = ["key,amount"]
    for key, quantity, base_cents in lines:
        unit = round(base_cents / 100.0 * (1 + state.TAX_RATE), 2)
        out.append("%s,%.2f" % (key, unit * quantity))
    return "\n".join(out) + "\n"


def total_cents(lines):
    return int(core.total(lines) * 100)
