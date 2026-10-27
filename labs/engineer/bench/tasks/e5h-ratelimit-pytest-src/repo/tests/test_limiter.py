from throttle import SlidingWindow


def test_limit_and_expiry():
    w = SlidingWindow(2, 10)
    assert w.allow("k", 0) and w.allow("k", 5)
    assert not w.allow("k", 9)
    assert w.allow("k", 10)


def test_keys_independent():
    w = SlidingWindow(1, 60)
    assert w.allow("a", 0)
    assert w.allow("b", 0)
    assert not w.allow("a", 1)


def test_instances_independent():
    SlidingWindow(1, 60).allow("shared", 0)
    assert SlidingWindow(1, 60).allow("shared", 0)
