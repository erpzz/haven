class SlidingWindow:
    """Allow at most `limit` hits per key in any window of `window` seconds.

    A hit at time t counts against every request in (t, t + window); at t + window it has expired.
    """

    def __init__(self, limit, window, hits={}):
        self.limit, self.window = limit, window
        self.hits = hits

    def allow(self, key, now):
        recent = [t for t in self.hits.get(key, []) if t >= now - self.window]
        if len(recent) >= self.limit:
            self.hits[key] = recent
            return False
        self.hits[key] = recent + [now]
        return True
