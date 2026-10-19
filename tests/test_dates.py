import pytest

from normt2s import Normalizer, normalize


def de(t):
    return normalize(t, "de")


@pytest.mark.parametrize("text,expected", [
    ("15.03.2024", "fünfzehnter März zweitausendvierundzwanzig"),
    ("am 15.03.2024", "am fünfzehnten März zweitausendvierundzwanzig"),
    ("vom 1.1.1999 bis zum 31.12.2000", "vom ersten Januar neunzehnhundertneunundneunzig bis zum einunddreißigsten Dezember zweitausend"),
    ("Der 3.10. ist ein Feiertag", "Der dritte Oktober ist ein Feiertag"),
    ("bis 15.03. erledigen", "bis fünfzehnter März erledigen"),
    ("am 3. Mai", "am dritten Mai"),
    ("Am 3. Mai 2024 war es so", "Am dritten Mai zweitausendvierundzwanzig war es so"),
    ("den 21. Juni", "den einundzwanzigsten Juni"),
    ("im Mai 2024", "im Mai zweitausendvierundzwanzig"),
    ("2024-03-15", "fünfzehnter März zweitausendvierundzwanzig"),
    ("Heute ist der 1. Februar.", "Heute ist der erste Februar."),
])
def test_german_dates(text, expected):
    assert de(text) == expected


@pytest.mark.parametrize("text", [
    "Version 1.2.3 ist da",            # not a date: stays a version
    "Er kam am 3. Tag",                # ordinal dot before a non-month
    "Es gibt 32.13.2024 Fälle",        # impossible date
    "1.000.000 Menschen",              # thousands separators
])
def test_german_non_dates_are_not_dates(text):
    out = de(text)
    assert "März" not in out and "Januar" not in out and "Dezember" not in out


def test_german_version_unchanged_semantics():
    assert de("Version 1.2.3") == "Version eins Punkt zwei Punkt drei".replace("Punkt", "Komma")


@pytest.mark.parametrize("text,expected", [
    ("March 3, 2024", "March third, twenty twenty-four"),
    ("on March 3rd", "on March third"),
    ("May 21", "May twenty-first"),
    ("in March 2024", "in March twenty twenty-four"),
    ("2024-03-15", "March fifteenth, twenty twenty-four"),
    ("December 25th, 1999.", "December twenty-fifth, nineteen ninety-nine."),
])
def test_english_dates(text, expected):
    assert normalize(text) == expected


def test_english_month_without_number_untouched():
    assert normalize("In March we left") == "In March we left"
