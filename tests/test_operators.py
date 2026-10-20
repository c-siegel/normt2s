import pytest

from normt2s import Normalizer


@pytest.fixture
def en():
    return Normalizer("en")


@pytest.mark.parametrize("src,want", [
    ("3 * 4 * 5", "three times four times five"),
    ("3*4*5", "three times four times five"),
    ("2*(x+1)", "two times (x plus one)"),
    ("3 / 4", "three divided by four"),
    ("1/2 cup", "one half cup"),
    ("and/or", "and/or"),
    ("a * b", "a * b"),
    ("**bold**", "**bold**"),
    ("F = m · a", "F equals m times a"),
    ("2·3", "two times three"),
    ("(a+b) · c", "(a plus b) times c"),
    ("Home · About", "Home · About"),
    ("x · Home", "x · Home"),
])
def test_operators(en, src, want):
    assert en.normalize(src) == want


def test_german_operators():
    de = Normalizer("de")
    assert de.normalize("3 * 4") == "drei mal vier"
    assert de.normalize("8 / 2") == "acht geteilt durch zwei"
    assert de.normalize("F = m · a") == "F gleich m mal a"
    assert de.normalize("Lehrer·innen") == "Lehrer·innen"
    assert de.normalize("Impressum · Datenschutz") == "Impressum · Datenschutz"


def test_add_symbol_any_char(en):
    en.add_symbol("@", "at")
    assert en.normalize("5 @ 3") == "five at three"
    en.add_symbol("!=", "is not")
    assert en.normalize("a != b") == "a is not b"


def test_add_symbol_star_is_infix(en):
    en.add_symbol("*", "star")
    assert en.normalize("a * b") == "a star b"


@pytest.mark.parametrize("key", ["", " ", "a b"])
def test_add_symbol_invalid(en, key):
    with pytest.raises(ValueError):
        en.add_symbol(key, "x")
