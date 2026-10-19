import random

import pytest

from normt2s import Normalizer, Rule, RuleSet

SENTENCES = [
    "The train goes 120 km/h.", "Dr. Smith pays $3.50 now.", "It is 3:45 pm, i.e. late.",
    "Use e.g. apples!", "Is 1/2 cup enough?", "Call 5 times.\n", "Next line here.\n",
    "See `code 5` and $x^2$ ok.", "In 1984 it cost 2 kg.", "Short.", "A longer sentence with "
    "many words, so that the buffer fills up a little more than usual.",
]
RULES = RuleSet([Rule("pH", "p H"), Rule("{number} kg", "{number} kilograms")])


def make_text(rnd):
    return "".join(rnd.choice(SENTENCES) + rnd.choice([" ", " ", "\n", "  "]) for _ in range(rnd.randint(1, 12)))


def chunks(text, rnd):
    i = 0
    while i < len(text):
        k = rnd.randint(1, 15)
        yield text[i:i + k]
        i += k


@pytest.mark.parametrize("lang", ["en", "de"])
def test_any_sizes_join_to_whole(lang):
    n = Normalizer(lang)
    for seed in range(120):
        rnd = random.Random(seed)
        text = make_text(rnd)
        first, minimum, mx = rnd.choice([0, 10, 25, 60]), rnd.choice([0, 20, 80, 200]), rnd.choice([30, 120, 400])
        s = n.stream(mx, first_min_chars=first, min_chars=minimum, rules=RULES)
        out = "".join(s.feed(c) for c in chunks(text, rnd)) + s.flush()
        assert out == n.normalize(text, rules=RULES), (seed, first, minimum, mx)


def test_defaults_are_unchanged_behaviour():
    n = Normalizer("en")
    text = "One. Two. Three. Four"
    a, b = n.stream(), n.stream(first_min_chars=0, min_chars=0)
    assert a.feed(text) == b.feed(text) == "One. Two. Three. "


def test_first_chunk_is_short_then_long():
    n = Normalizer("en")
    text = "Hello there. This is the second sentence. And the third one. Fourth"
    s = n.stream(first_min_chars=10, min_chars=30)
    assert s.feed(text) == "Hello there. "
    assert s.feed("") == "This is the second sentence. And the third one. "


def test_min_chars_waits():
    n = Normalizer("en")
    s = n.stream(min_chars=30)
    assert s.feed("Short one. ") == ""
    assert s.feed("Another short one. ") == "Short one. Another short one. "
    assert s.flush() == ""


def test_first_min_chars_waits_for_a_long_enough_boundary():
    n = Normalizer("en")
    s = n.stream(first_min_chars=25)
    assert s.feed("Hi. Ok. ") == ""
    assert s.feed("Now this one is long enough. Tail") == "Hi. Ok. Now this one is long enough. "


def test_flush_ignores_min_chars():
    n = Normalizer("en")
    s = n.stream(first_min_chars=500, min_chars=500)
    s.feed("Tiny. ")
    assert s.flush() == "Tiny. "


def test_max_buffer_fallback_unchanged():
    n = Normalizer("en")
    s = n.stream(max_buffer=20, min_chars=1000)
    out = s.feed("word " * 20)
    assert out and out.endswith(" ")


def test_normalize_stream_sizes():
    n = Normalizer("en")
    text = "Hello there. This is the second sentence. And the third one. Fourth"
    got = list(n.normalize_stream(iter([text, ""]), first_min_chars=10, min_chars=30))
    assert got == ["Hello there. ", "This is the second sentence. And the third one. ", "Fourth"]
