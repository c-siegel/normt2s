import pytest

from normt2s import Normalizer, Rule, RuleSet


@pytest.fixture(scope="module")
def de():
    return Normalizer("de")


@pytest.fixture(scope="module")
def en():
    return Normalizer("en")


@pytest.mark.parametrize("src,want", [
    ("1 rad", "ein Radiant"),
    ("5 mSv", "fünf Millisievert"),
    ("1 Gy", "ein Gray"),
    ("3 MBq", "drei Megabecquerel"),
    ("300 mK", "dreihundert Millikelvin"),
    ("1 Kelvin", "ein Kelvin"),          # nouns of prefix-only bases have a gender
    ("1 Farad", "ein Farad"),
    ("4K", "vier K"),                     # no bare single-capital bases
    ("Klasse 5A", "Klasse fünf A"),
    ("1 t", "eine Tonne"),
])
def test_german_base_units(de, src, want):
    assert de.normalize(src) == want


def test_rule_noun_of_prefix_only_base(de):
    rules = RuleSet([Rule("{number} K", "{number} Kelvin")])
    assert de.normalize("T = 1 K", rules=rules) == "T gleich ein Kelvin"


def test_english_tonne(en):
    assert en.normalize("2 t") == "two tonnes"


def test_ohm_with_a_space():
    assert Normalizer("en").normalize("R = 5 Ω") == "R equals five ohms"
