def merge(intervals):
    """Merge overlapping or touching (start, end) intervals."""
    out = []
    for start, end in sorted(intervals, key=lambda iv: iv[1]):
        if out and start < out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out
