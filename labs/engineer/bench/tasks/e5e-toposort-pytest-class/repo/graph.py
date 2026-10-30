import heapq


class CycleError(Exception):
    pass


def order(deps):
    """Build order for {target: [dependencies]}. Ties break alphabetically. Dependencies need not be keys."""
    indeg = {n: len(ds) for n, ds in deps.items()}
    users = {}
    for n, ds in deps.items():
        for d in ds:
            users.setdefault(d, []).append(n)
    ready = [n for n, k in indeg.items() if k == 0]
    out = []
    while ready:
        n = ready.pop(0)
        out.append(n)
        for u in users.get(n, []):
            indeg[u] -= 1
            if indeg[u] == 0:
                ready.append(u)
    if len(out) != len(indeg):
        raise CycleError(sorted(set(indeg) - set(out)))
    return out
