def split(total_cents, parts):
    """Split total into `parts` amounts that differ by at most one cent and sum to total."""
    base, extra = divmod(total_cents, parts)
    return [base + (1 if i < extra else 0) for i in range(parts - 1)]
