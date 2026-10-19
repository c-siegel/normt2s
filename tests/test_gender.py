import pytest

from normt2s import Normalizer


@pytest.fixture
def de():
    return Normalizer("de")


@pytest.mark.parametrize("src,want", [
    ("1 Stunde", "eine Stunde"),
    ("1 Minute", "eine Minute"),
    ("1 Kilogramm", "ein Kilogramm"),
    ("21 Stunden", "einundzwanzig Stunden"),
    ("21 Minuten", "einundzwanzig Minuten"),
    ("101 Stunden", "einhunderteins Stunden"),
    ("Es dauert 1 Stunde und 1 Minute.", "Es dauert eine Stunde und eine Minute."),
    ("1 Haus", "eins Haus"),
    ("1 h", "eine Stunde"),
    ("1,5 Stunden", "eins Komma fünf Stunden"),
    ("1,5 kg", "eins Komma fünf Kilogramm"),
    ("-1 Stunde", "minus eine Stunde"),
    ("1\nStunde", "eins\nStunde"),
    ("1  Stunde", "eins  Stunde"),
])
def test_german(de, src, want):
    assert de.normalize(src) == want


def test_english_is_unaffected():
    en = Normalizer("en")
    assert en.normalize("1 hour and 1 minute") == "one hour and one minute"


def test_user_unit_noun_gender(de):
    de.add_unit("Std", "Stunde", "Stunden", "f")
    de.add_unit("Bd", "Band", "Bände", "m")
    assert de.normalize("1 Band") == "ein Band"
