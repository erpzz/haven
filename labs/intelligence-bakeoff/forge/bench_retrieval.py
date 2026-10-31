"""Compare identical offline retrieval results with and without an index cache."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).parent / ".hermes/plugins/haven-forge"))
from forge_runtime.knowledge import load_cards, search


QUERIES = ("report-only policy state", "AND OR compliantDevice grant controls",
           "sign-in coverage applied evidence")


def run(iterations: int, repetitions: int) -> dict:
    before = [search(query, cards=load_cards()) for query in QUERIES]
    after = [search(query) for query in QUERIES]
    if before != after:
        raise RuntimeError("Cached and fresh retrieval outputs differ")
    samples = {"fresh": [], "cached": []}
    for repetition in range(repetitions):
        order = ("fresh", "cached") if repetition % 2 == 0 else ("cached", "fresh")
        for mode in order:
            started = time.perf_counter_ns()
            for _ in range(iterations):
                for query in QUERIES:
                    result = search(query, cards=load_cards()) if mode == "fresh" else search(query)
                    if not result:
                        raise RuntimeError("Expected synthetic retrieval hit was missing")
            samples[mode].append((time.perf_counter_ns() - started) / (iterations * len(QUERIES)))
    medians = {mode: statistics.median(values) / 1000 for mode, values in samples.items()}
    return {"query_count_per_sample": iterations * len(QUERIES), "samples": repetitions,
            "median_microseconds_per_query": medians, "speedup": medians["fresh"] / medians["cached"],
            "exact_results_equal": before == after, "model_calls": 0, "network_calls": 0,
            "scope": "warm local FTS5 retrieval for three project-authored cards"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--repetitions", type=int, default=7)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 5000 or not 1 <= args.repetitions <= 20:
        parser.error("iterations must be 1–5000 and repetitions 1–20")
    print(json.dumps(run(args.iterations, args.repetitions), indent=2))


if __name__ == "__main__":
    main()
