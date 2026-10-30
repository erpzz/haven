from slots.intervals import merge


def free_slots(busy, day_start, day_end, min_len=1):
    """Gaps of at least min_len between busy intervals inside [day_start, day_end]."""
    gaps, cursor = [], day_start
    for start, end in merge(busy):
        if start - cursor >= min_len:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if day_end - cursor >= min_len:
        gaps.append((cursor, day_end))
    return gaps
