import pytest

from normt2s import Normalizer, Rule, RuleSet


@pytest.fixture(scope="module")
def de():
    return Normalizer("de")


@pytest.fixture(scope="module")
def en():
    return Normalizer("en")


@pytest.mark.parametrize("src,want", [
    ("Δt = 5 s", "Delta t gleich fünf Sekunden"),
    ("α-Teilchen", "Alpha-Teilchen"),
    ("2π r", "zwei Pi r"),
    ("ℏω", "h quer Omega"),
    ("σ²", "Sigma zum Quadrat"),
    ("(α)", "(Alpha)"),
    ("µ = 0,3", "My gleich null Komma drei"),
    ("μ-Wert", "My-Wert"),
    ("5 µm", "fünf Mikrometer"),       # µ before a unit is the prefix
    ("in µm", "in µm"),                # ... and is not read as a letter
    ("Ελλάδα", "Ελλάδα"),              # Greek words are left alone
    ("in Ω", "in Ohm"),
    ("a ∝ b", "a ist proportional zu b"),
    ("x → ∞", "x nach unendlich"),
    ("A ⇒ B", "A daraus folgt B"),
    ("√2 ist irrational", "Wurzel aus zwei ist irrational"),
    ("0,5‰ Alkohol.", "null Komma fünf Promille Alkohol."),
    ("½ Liter", "ein halb Liter"),
    ("1½ Stunden", "eineinhalb Stunden"),
    ("2 ¾", "zweidreiviertel"),
    ("(×)", "(mal)"),
    ("× 3", "mal drei"),
])
def test_german_symbols(de, src, want):
    assert de.normalize(src) == want


@pytest.mark.parametrize("src,want", [
    ("ΔT", "delta T"),
    ("λ = 500 nm", "lambda equals five hundred nanometers"),
    ("R = 5 Ω", "R equals five ohms"),
    ("1½ cups", "one and a half cups"),
    ("2¼", "two and a quarter"),
    ("x → ∞", "x to infinity"),
])
def test_english_symbols(en, src, want):
    assert en.normalize(src) == want


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


@pytest.mark.parametrize("src,want", [
    ("5 W/m²", "fünf Watt pro Quadratmeter"),   # a spaced capital is a unit before "/"
    ("10 V/m", "zehn Volt pro Meter"),
    ("Klasse 5 A/B", "Klasse fünf A/B"),
    ("40 Nm", "vierzig Newtonmeter"),
    ("5 N·m", "fünf Newtonmeter"),               # not "N mal m"
    ("2 kN·m", "zwei Kilonewtonmeter"),
    ("3 W·s", "drei Wattsekunden"),
    ("2 kVA", "zwei Kilovoltampere"),
    ("2000 mAh", "zweitausend Milliamperestunden"),
    ("F = m · a", "F gleich m mal a"),
])
def test_german_compound_units(de, src, want):
    assert de.normalize(src) == want


def test_english_compound_units(en):
    assert en.normalize("5 W/m² and 40 Nm") == "five watts per square meter and forty newton meters"
