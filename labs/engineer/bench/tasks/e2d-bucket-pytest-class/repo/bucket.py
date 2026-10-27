class TokenBucket:
    def __init__(self, capacity, refill_per_s):
        self.capacity = capacity
        self.tokens = capacity
        self.rate = refill_per_s
        self.t = 0.0

    def take(self, now, n=1):
        self.tokens = min(self.capacity, self.tokens + (now - self.t) * self.rate)
        self.t = now
        if self.tokens > n:
            self.tokens -= n
            return True
        return False
