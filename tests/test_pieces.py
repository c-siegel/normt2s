import random

import pytest

from normt2s import Normalizer, Piece, Rule, RuleSet
from test_stream_sizes import chunks, make_text

DOC = ("# Title\n\nSome **bold** text costs $3.50, i.e. cheap. See [a link](http://x.org/a_b).\n"
       "- item 1. One\n```python\nprint(1 + 2)\n```\nFinal 3*4 km.")


def test_piece_is_a_named_tuple():
    p = Piece("raw", "spoken")
    assert p.raw == "raw" and p.spoken == "spoken" and tuple(p) == ("raw", "spoken")


def test_feed_pieces_and_flush_piece():
    n = Normalizer("en")
    s = n.stream()
    assert s.feed_pieces("It weighs 3") == []
    pieces = s.feed_pieces(".5 kg now. And")
    assert pieces == [Piece("It weighs 3.5 kg now. ", "It weighs three point five kilograms now. ")]
    last = s.flush_piece()
    assert last == Piece("And", "And")
    assert s.flush_piece() is None
    assert s.flush() == ""


def test_several_pieces_from_one_token():
    n = Normalizer("en")
    s = n.stream(first_min_chars=5, min_chars=30)
    pieces = s.feed_pieces("Hello there. This is the second sentence. And the third one. Fourth")
    assert [p.raw for p in pieces] == ["Hello there. ", "This is the second sentence. And the third one. "]


def test_empty_spoken_piece_keeps_raw():
    n = Normalizer("en", markdown="strip")
    s = n.stream()
    pieces = s.feed_pieces("---\nText\n")
    assert "".join(p.raw for p in pieces) == "---\nText\n"
    assert pieces[0].spoken in ("\n", "") or pieces[0].raw


def test_feed_matches_pieces():
    n = Normalizer("en")
    a, b = n.stream(first_min_chars=5), n.stream(first_min_chars=5)
    text = "One two. Three four. Five six."
    assert a.feed(text) == "".join(p.spoken for p in b.feed_pieces(text))


@pytest.mark.parametrize("opts", [{}, {"markdown": "strip"}])
def test_pieces_join_to_input_and_to_normalized(opts):
    n = Normalizer("en", **opts)
    rules = RuleSet([Rule("pH", "p H")])
    texts = [DOC] + [make_text(random.Random(k)) for k in range(30)]
    for text in texts:
        for seed in range(15):
            rnd = random.Random(seed)
            s = n.stream(rnd.choice([100, 400]), first_min_chars=rnd.choice([0, 12]),
                         min_chars=rnd.choice([0, 40]), rules=rules)
            pieces = []
            for c in chunks(text, rnd):
                pieces += s.feed_pieces(c)
            last = s.flush_piece()
            if last:
                pieces.append(last)
            assert "".join(p.raw for p in pieces) == text
            assert "".join(p.spoken for p in pieces) == n.normalize(text, rules)


def test_normalize_stream_yields_pieces():
    n = Normalizer("en")
    got = list(n.normalize_stream(["Hello there. This is it. ", "More"], first_min_chars=5))
    assert "".join(got) == n.normalize("Hello there. This is it. More")
