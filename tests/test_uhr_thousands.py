import pytest

from normt2s import Normalizer


@pytest.mark.parametrize("src,want", [
    ("um 14:30 Uhr", "um vierzehn Uhr dreißig"),
    ("um 14:30 uhr", "um vierzehn Uhr dreißig uhr"),
    ("um 8:05Uhr", "um acht Uhr fünf"),
    ("um 14:30 Uhrzeit", "um vierzehn Uhr dreißig Uhrzeit"),
    ("um 14:30", "um vierzehn Uhr dreißig"),
    ("1 000 Äpfel", "eintausend Äpfel"),
    ("12 345,5 kg", "zwölftausenddreihundertfünfundvierzig Komma fünf Kilogramm"),
    ("1 000 000", "eine Million"),
    ("5 12 3", "fünf zwölf drei"),
    ("2024 100", "zweitausendvierundzwanzig einhundert"),
    ("3 1000", "drei eintausend"),
])
def test_german(src, want):
    assert Normalizer("de").normalize(src) == want


@pytest.mark.parametrize("src,want", [
    ("1 000 apples", "one thousand apples"),
    ("1 234 567.5 kg", "one million two hundred thirty-four thousand five hundred sixty-seven point five kilograms"),
    ("1,000 apples", "one thousand apples"),
    ("3 100 and 4 20", "three thousand one hundred and four twenty"),
    ("at 5:00 Uhr", "at five o'clock Uhr"),
])
def test_english(src, want):
    assert Normalizer("en").normalize(src) == want
