from decimal import Decimal

from billing.money import to_cents


class Invoice:
    def __init__(self, tax_rate, discount=Decimal("0")):
        self.tax_rate = Decimal(tax_rate)
        self.discount = Decimal(discount)  # fraction off the subtotal, applied before tax
        self.lines = []

    def add(self, unit_price, qty=1):
        self.lines.append((Decimal(unit_price), qty))

    def subtotal(self):
        return to_cents(sum(p * q for p, q in self.lines))

    def total(self):
        taxed = self.subtotal() * (1 + self.tax_rate)
        return to_cents(taxed * (1 - self.discount))
