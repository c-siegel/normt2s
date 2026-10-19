import pytest

from normt2s import Normalizer, normalize

N = Normalizer("de")


def de(text):
    return normalize(text, "de")


@pytest.mark.parametrize("n,expected", [
    (0, "null"), (1, "eins"), (12, "zwölf"), (16, "sechzehn"), (21, "einundzwanzig"),
    (30, "dreißig"), (99, "neunundneunzig"), (100, "einhundert"), (101, "einhunderteins"),
    (1000, "eintausend"), (1001, "eintausendeins"), (2024, "zweitausendvierundzwanzig"),
    (21_000, "einundzwanzigtausend"), (100_000, "einhunderttausend"),
    (1_000_000, "eine Million"), (2_000_000, "zwei Millionen"),
    (2_500_000, "zwei Millionen fünfhunderttausend"), (1_000_000_000, "eine Milliarde"),
    (-3, "minus drei"),
])
def test_cardinal(n, expected):
    assert N.lang.cardinal(n) == expected


@pytest.mark.parametrize("n,expected", [
    (1, "erste"), (2, "zweite"), (3, "dritte"), (4, "vierte"), (7, "siebte"), (8, "achte"),
    (12, "zwölfte"), (19, "neunzehnte"), (20, "zwanzigste"), (21, "einundzwanzigste"),
    (100, "einhundertste"), (103, "einhundertdritte"),
])
def test_ordinal(n, expected):
    assert N.lang.ordinal(n) == expected


@pytest.mark.parametrize("text,expected", [
    ("Ich habe 3 Äpfel.", "Ich habe drei Äpfel."),
    ("Pi ist 3,14", "Pi ist drei Komma eins vier"),
    ("1.234.567 Menschen", "eine Million zweihundertvierunddreißigtausendfünfhundertsiebenundsechzig Menschen"),
    ("1.234,5", "eintausendzweihundertvierunddreißig Komma fünf"),
    ("50 % davon", "fünfzig Prozent davon"),
    ("-5 Grad", "minus fünf Grad"),
    ("10–20 Stück", "zehn bis zwanzig Stück"),
    ("im Jahr 1984", "im Jahr neunzehnhundertvierundachtzig"),
    ("seit 2024", "seit zweitausendvierundzwanzig"),
])
def test_numbers(text, expected):
    assert de(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("1 km", "ein Kilometer"),
    ("5 km", "fünf Kilometer"),
    ("1 min", "eine Minute"),
    ("21 min", "einundzwanzig Minuten"),
    ("1 kg", "ein Kilogramm"),
    ("100 km/h", "einhundert Kilometer pro Stunde"),
    ("20°C", "zwanzig Grad Celsius"),
    ("9,81 m/s²", "neun Komma acht eins Meter pro Sekunde zum Quadrat"),
])
def test_units(text, expected):
    assert de(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("5 €", "fünf Euro"),
    ("€5", "fünf Euro"),
    ("3,50 €", "drei Euro fünfzig Cent"),
    ("1 €", "ein Euro"),
    ("0,99 €", "neunundneunzig Cent"),
    ("2 Mio. Euro", "zwei Millionen Euro"),
])
def test_currency(text, expected):
    assert de(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("um 14:30", "um vierzehn Uhr dreißig"),
    ("um 9:00", "um neun Uhr"),
    ("um 1:15", "um ein Uhr fünfzehn"),
    ("1/2 Liter", "ein halb Liter"),
    ("1/3", "ein drittel"),
    ("3/4", "drei viertel"),
    ("2/5", "zwei fünftel"),
])
def test_time_and_fractions(text, expected):
    assert de(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("z. B. heute", "zum Beispiel heute"),
    ("z.B. heute", "zum Beispiel heute"),
    ("Z. B. heute", "Zum Beispiel heute"),
    ("ca. 5 km", "circa fünf Kilometer"),
    ("Dr. Müller", "Doktor Müller"),
    ("Äpfel, Birnen usw.", "Äpfel, Birnen und so weiter."),
    ("2 + 3 = 5", "zwei plus drei gleich fünf"),
])
def test_abbreviations_and_symbols(text, expected):
    assert de(text) == expected
