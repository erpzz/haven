"""Word statistics for article bodies."""
from collections import Counter


def top_words(text: str, n: int = 3):
    """The n most common words (case-insensitive), ties broken alphabetically."""
    counts = Counter(w.lower() for w in text.split())
    return [w for w, _ in sorted(counts.items(), key=lambda kv: (kv[1], kv[0]))][:n]
