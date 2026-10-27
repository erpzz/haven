"""Order pricing for the sample shop."""


def line_total(unit_price_cents: int, quantity: int) -> int:
    if quantity < 0:
        raise ValueError("quantity must be non-negative")
    return unit_price_cents * quantity


def apply_discount(total_cents: int, percent: int) -> int:
    """Return the total after a percentage discount, rounded down to whole cents."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return total_cents * percent // 100


def order_total(lines, discount_percent: int = 0) -> int:
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    return apply_discount(subtotal, discount_percent)
