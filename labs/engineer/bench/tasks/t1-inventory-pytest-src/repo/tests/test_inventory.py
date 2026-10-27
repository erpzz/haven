import pytest
from inventory import Inventory

def test_receive_and_ship():
    inv = Inventory(); inv.receive('bolt', 10); inv.ship('bolt', 4)
    assert inv.stock['bolt'] == 6

def test_cannot_oversell():
    inv = Inventory(); inv.receive('nut', 1)
    with pytest.raises(ValueError):
        inv.ship('nut', 2)

def test_low_stock():
    inv = Inventory(); inv.receive('a', 1); inv.receive('b', 9)
    assert inv.low(5) == ['a']
