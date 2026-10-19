import pytest

from normt2s import Normalizer


@pytest.mark.parametrize("src,want", [
    ("The result — a success — was clear.", "The result, a success, was clear."),
    ("The result—a success—was clear.", "The result, a success, was clear."),
    ("10—20 km", "ten to twenty kilometers"),
    ("10–20 km", "ten to twenty kilometers"),
    ("5 - 3", "five minus three"),
    ("— Hello there", "Hello there"),
    ("Line one\n— Line two", "Line one\nLine two"),
    ("Wait —", "Wait"),
    ("Yes, — no", "Yes, no"),
    ("Well —. Done", "Well. Done"),
])
def test_em_dash(src, want):
    assert Normalizer("en").normalize(src) == want


def test_german():
    assert Normalizer("de").normalize("Das Ergebnis — ein Erfolg — war klar.") == \
        "Das Ergebnis, ein Erfolg, war klar."


def test_add_punctuation():
    n = Normalizer("en")
    n.add_punctuation("…", " dot dot dot ")
    assert n.normalize("Hmm… ok") == "Hmm dot dot dot ok"
    with pytest.raises(ValueError):
        n.add_punctuation("ab", "x")
