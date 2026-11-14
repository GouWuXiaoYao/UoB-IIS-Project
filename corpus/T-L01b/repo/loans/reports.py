from loans import core, state


def summarise(lines):
    amount = core.total(lines)
    return "GBP {:.2f} ({} items, tax {:.0f}%)".format(
        amount, len(lines), state.TAX_RATE * 100
    )
