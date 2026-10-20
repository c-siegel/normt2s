import random

import pytest

from normt2s import Normalizer, Piece
from normt2s.lexicon import _leading_literal


@pytest.fixture
def n():
    n = Normalizer("en")
    n.add_protected(r"::[a-z_]+::")
    n.add_protected(r"\[\d+\]", spoken="")
    n.add_protected(r"\[laughs\]")
    n.add_protected(r"<emotion:\w+>")
    return n


def test_kept_verbatim(n):
    assert n.normalize("Hi ::wave:: there 5 kg") == "Hi ::wave:: there five kilograms"
    assert n.normalize("[laughs] ok <emotion:happy> 3") == "[laughs] ok <emotion:happy> three"


def test_dropped_from_spoken_text(n):
    assert n.normalize("It is 5 km [1] away.") == "It is five kilometers away."
    assert n.normalize("It is far.[2] Next [3], then") == "It is far. Next, then"
    assert n.normalize("[1] Start") == "Start"
    assert n.normalize("End of line [12]") == "End of line"
    assert n.normalize("a[1]b") == "ab"


def test_replacement_text():
    n = Normalizer("en")
    n.add_protected(r"\(c\)", spoken="copyright")
    assert n.normalize("(c) 2024") == "copyright two thousand twenty-four"


def test_marker_separates_number_and_unit(n):
    assert n.normalize("5 ::wave:: kg") == "five ::wave:: kg"


def test_marker_inside_markdown_and_math():
    n = Normalizer("en", markdown="strip")
    n.add_protected(r"::[a-z_]+::")
    assert n.normalize("**hi ::big_wave:: there**") == "hi ::big_wave:: there"
    assert n.normalize("_a ::x_y:: b_") == "a ::x_y:: b"


@pytest.mark.parametrize("bad,kw", [
    ("(unclosed", {}),
    (r"(a)b", {}),
    (r"a*", {}),
    (r"(?i)abc", {}),
    (r"\d+", {}),
])
def test_invalid_patterns_raise(bad, kw):
    with pytest.raises(ValueError):
        Normalizer("en").add_protected(bad, **kw)


def test_opener_required_or_explicit():
    n = Normalizer("en")
    n.add_protected(r"\d{3}-\d{4}", opener="")
    assert n.normalize("call 555-1234 now 5") == "call 555-1234 now five"


def test_scoped_flags_are_fine():
    n = Normalizer("en")
    n.add_protected(r"(?i:\[todo\])", opener="")
    assert n.normalize("[TODO] 5") == "[TODO] five"


def test_leading_literal():
    assert _leading_literal(r"::[a-z_]+::") == "::"
    assert _leading_literal(r"\[\d+\]") == "["
    assert _leading_literal(r"<emotion:\w+>") == "<emotion:"
    assert _leading_literal(r"\[laughs\. loudly\]") == "[laughs"
    assert _leading_literal(r"ab*c") == "a"
    assert _leading_literal(r"\d+") == ""
    assert _leading_literal(r"(?<![\w:])::[a-z_]+::(?![\w:])") == "::"
    assert _leading_literal(r"^\b(?=<)(?<![\]:])<tag>") == "<tag>"
    assert _leading_literal(r"(?<=x)\d") == ""


def test_guarded_marker_needs_no_opener():
    n = Normalizer("en")
    n.add_protected(r"(?<![\w:])::[a-z_]+::(?![\w:])", spoken="")
    assert n.normalize("Call std::vector::size ::wave:: now") == "Call std::vector::size now"


def test_lexicon_file(tmp_path):
    import json

    path = tmp_path / "lex.json"
    path.write_text(json.dumps({"protected": [r"::[a-z]+::", {"pattern": r"\[\d+\]", "spoken": ""}]}), "utf-8")
    n = Normalizer("en")
    n.load_lexicon(path)
    assert n.normalize("a ::x:: b [4] 2") == "a ::x:: b two"


def test_other_instances_unaffected(n):
    assert Normalizer("en").normalize("[1] 5") == "[one] five"


# ---------------------------------------------------------------------------- streaming
TEXT = ("Hello there ::wave:: friend, it costs 5 kg [1] today. [laughs] Then <emotion:happy> "
        "we met 3 people at 3:45 pm [22]. Done ::big_wave::\nLast line 2 ::x::")


def _chunks(text, rnd, hi):
    i = 0
    while i < len(text):
        k = rnd.randint(1, hi)
        yield text[i:i + k]
        i += k


def test_marker_split_across_chunks(n):
    want = n.normalize(TEXT)
    for seed in range(120):
        rnd = random.Random(seed)
        s = n.stream(first_min_chars=rnd.choice([0, 10]), min_chars=rnd.choice([0, 30]))
        out = "".join(s.feed(c) for c in _chunks(TEXT, rnd, rnd.choice([2, 3, 5]))) + s.flush()
        assert out == want, seed


def test_marker_with_sentence_mark_is_held_back():
    n = Normalizer("en")
    n.add_protected(r"\[laughs\. loudly\]", spoken="")
    s = n.stream()
    text = "He said it. [laughs. loudly] Then left."
    pieces = []
    for i in range(0, len(text), 3):
        pieces += s.feed_pieces(text[i:i + 3])
    last = s.flush_piece()
    pieces.append(last)
    assert "".join(p.raw for p in pieces) == text
    assert "".join(p.spoken for p in pieces) == n.normalize(text) == "He said it. Then left."


def test_dropped_marker_keeps_raw_in_pieces(n):
    s = n.stream()
    pieces = s.feed_pieces("Look here [1]. Next one [2].\n")
    assert "".join(p.raw for p in pieces) == "Look here [1]. Next one [2].\n"
    assert all(isinstance(p, Piece) for p in pieces)
    assert "".join(p.spoken for p in pieces) == "Look here. Next one.\n"
