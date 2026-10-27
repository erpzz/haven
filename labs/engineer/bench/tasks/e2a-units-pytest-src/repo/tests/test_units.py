import pytest
from units import c_to_f, f_to_c, km_to_miles

def test_boiling():
    assert c_to_f(100) == 212

def test_round_trip():
    assert abs(f_to_c(c_to_f(37)) - 37) < 1e-9

def test_negative_distance():
    with pytest.raises(ValueError):
        km_to_miles(-1)
