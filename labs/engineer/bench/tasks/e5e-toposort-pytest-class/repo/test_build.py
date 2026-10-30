import pytest

from graph import CycleError, order


class TestOrder:
    def test_alphabetical_ties(self):
        assert order({"b": [], "a": [], "c": ["b", "a"]}) == ["a", "b", "c"]

    def test_implicit_leaves(self):
        assert order({"app": ["lib", "util"], "lib": ["util"]}) == ["util", "lib", "app"]

    def test_ready_order_after_release(self):
        assert order({"z": [], "y": ["z"], "a": ["z"]}) == ["z", "a", "y"]

    def test_cycle(self):
        with pytest.raises(CycleError):
            order({"a": ["b"], "b": ["a"]})
