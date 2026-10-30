from decimal import Decimal


def to_cents(amount):
    """Round a Decimal amount of dollars to whole cents, halves away from zero."""
    return Decimal(round(amount * 100)) / 100
