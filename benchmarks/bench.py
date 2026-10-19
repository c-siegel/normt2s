"""Latency benchmark:  python benchmarks/bench.py"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import random  # noqa: E402

from normt2s import Normalizer, Rule, RuleSet  # noqa: E402

SENTENCE = "The train travels at 120 km/h and left at 3:45 pm, i.e. in 1984 for $3.50."
PARAGRAPH = (SENTENCE + " Dr. Smith measured 9.81 m/s² and 2 + 3 = 5.\n") * 5
MARKDOWN = (
    "## Plan\n- **Walk** 3*4 km, see [the map](https://example.com/a_b)\n"
    "1. Take `pip install x` and _rest_ for 5 min\n> A ~~quote~~ with 2 + 3 = 5.\n"
) * 5
PLAIN = "This sentence has no numbers, units or abbreviations at all, just words. " * 5


def bench(n: Normalizer, text: str, loops: int = 5000) -> float:
    n.normalize(text)  # warm up (compiles regexes)
    t = time.perf_counter()
    for _ in range(loops):
        n.normalize(text)
    return (time.perf_counter() - t) / loops * 1e6


def main() -> None:
    t = time.perf_counter()
    n = Normalizer("en")
    n.normalize("1")
    print(f"import-free startup (build + compile): {(time.perf_counter() - t) * 1e3:.1f} ms")
    for name, text in (("sentence", SENTENCE), ("paragraph", PARAGRAPH), ("plain text", PLAIN)):
        print(f"{name:>10} ({len(text):4d} chars): {bench(n, text):8.1f} µs")

    md = Normalizer("en", markdown="strip")
    print(f"{'markdown':>10} ({len(MARKDOWN):4d} chars): {bench(md, MARKDOWN):8.1f} µs")
    rnd = random.Random(7)
    rules = RuleSet([Rule("".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(7)), "x")
                     for _ in range(200)])
    rules.rules  # noqa: B018
    n.normalize(SENTENCE, rules=rules)
    t = time.perf_counter()
    for _ in range(5000):
        n.normalize(SENTENCE, rules=rules)
    print(f"sentence with a 200-rule RuleSet:    {(time.perf_counter() - t) / 5000 * 1e6:8.1f} µs")

    s = n.stream()
    t = time.perf_counter()
    for _ in range(200):
        for i in range(0, len(PARAGRAPH), 4):  # ~token-sized chunks
            s.feed(PARAGRAPH[i:i + 4])
        s.flush()
    per = (time.perf_counter() - t) / 200 * 1e6
    print(f"streaming paragraph, 4-char chunks: {per:8.1f} µs total")

    text = (PARAGRAPH * 2)[:1000]
    t = time.perf_counter()
    for _ in range(20):
        s = n.stream()
        for ch in text:
            s.feed(ch)
        s.flush()
    per = (time.perf_counter() - t) / 20 * 1e3
    print(f"streaming 1,000 one-character chunks: {per:6.1f} ms total")


if __name__ == "__main__":
    main()
