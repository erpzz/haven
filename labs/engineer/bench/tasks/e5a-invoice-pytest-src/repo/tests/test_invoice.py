from decimal import Decimal as D

from billing.invoice import Invoice
from billing.money import to_cents


def test_half_cent_rounds_up():
    assert to_cents(D("0.125")) == D("0.13")
    assert to_cents(D("2.675")) == D("2.68")


def test_subtotal():
    inv = Invoice("0")
    inv.add("1.005", 1)
    assert inv.subtotal() == D("1.01")


def test_discount_before_tax():
    inv = Invoice("0.10", discount="0.15")
    inv.add("19.99", 3)
    # subtotal 59.97, discount -> 50.9745 -> 50.97, tax 10% -> 56.067 -> 56.07
    assert inv.total() == D("56.07")


def test_discount_rounds_before_tax():
    inv = Invoice("0.10", discount="0.5")
    inv.add("0.99")
    # 0.495 -> 0.50 after discount, then tax -> 0.55
    assert inv.total() == D("0.55")


def test_no_discount():
    inv = Invoice("0.0825")
    inv.add("10.00", 2)
    inv.add("0.35", 1)
    assert inv.total() == D("22.03")
