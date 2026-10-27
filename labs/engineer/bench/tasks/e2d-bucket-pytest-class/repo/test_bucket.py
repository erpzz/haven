from bucket import TokenBucket

class TestBucket:
    def test_drains_to_zero(self):
        b = TokenBucket(2, 1)
        assert b.take(0) and b.take(0)
        assert not b.take(0)

    def test_refills(self):
        b = TokenBucket(1, 1)
        assert b.take(0)
        assert b.take(1.0)
