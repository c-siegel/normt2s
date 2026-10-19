import pytest

from normt2s import Normalizer, normalize

N = Normalizer("en")


@pytest.mark.parametrize("n,expected", [
    (0, "zero"), (7, "seven"), (13, "thirteen"), (21, "twenty-one"), (100, "one hundred"),
    (101, "one hundred one"), (1000, "one thousand"), (1234, "one thousand two hundred thirty-four"),
    (1_000_000, "one million"), (2_000_003, "two million three"),
    (-5, "minus five"),
])
def test_cardinal(n, expected):
    assert N.lang.cardinal(n) == expected


@pytest.mark.parametrize("n,expected", [
    (1, "first"), (2, "second"), (3, "third"), (4, "fourth"), (5, "fifth"), (12, "twelfth"),
    (20, "twentieth"), (21, "twenty-first"), (100, "one hundredth"), (101, "one hundred first"),
])
def test_ordinal(n, expected):
    assert N.lang.ordinal(n) == expected


@pytest.mark.parametrize("text,expected", [
    ("I have 3 apples.", "I have three apples."),
    ("Pi is 3.14", "Pi is three point one four"),
    ("It is 0.5 long", "It is zero point five long"),
    ("1,234,567 people", "one million two hundred thirty-four thousand five hundred sixty-seven people"),
    ("It was -5 degrees", "It was minus five degrees"),
    ("the 1st, 2nd and 23rd", "the first, second and twenty-third"),
    ("50% of 200", "fifty percent of two hundred"),
    ("PIN 007", "PIN zero zero seven"),
    ("Section 3.2.1 says", "Section three point two point one says"),
    ("Windows 11 and H2O and mp3", "Windows eleven and H two O and mp3"),
    ("a 3D model", "a three D model"),
    ("10–20 items", "ten to twenty items"),
])
def test_numbers(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("in 1984", "in nineteen eighty-four"),
    ("in 2005", "in two thousand five"),
    ("since 2024", "since twenty twenty-four"),
    ("in 1905", "in nineteen oh five"),
    ("I have 1984 apples", "I have one thousand nine hundred eighty-four apples"),
    ("the 1990s", "the nineteen nineties"),
    ("the 1900s", "the nineteen hundreds"),
])
def test_years(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("5 km", "five kilometers"),
    ("1 km", "one kilometer"),
    ("1.5 kg", "one point five kilograms"),
    ("100 km/h", "one hundred kilometers per hour"),
    ("9.81 m/s²", "nine point eight one meters per second squared"),
    ("20°C", "twenty degrees Celsius"),
    ("5 m²", "five square meters"),
    ("3 GHz", "three gigahertz"),
    ("12V", "twelve volts"),
    ("5 million", "five million"),
    ("I have 5 A", "I have five A"),  # single capital letters need to be attached
    ("1 ft and 2 ft", "one foot and two feet"),
])
def test_units(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("$5", "five dollars"),
    ("$1", "one dollar"),
    ("$3.50", "three dollars and fifty cents"),
    ("$0.99", "ninety-nine cents"),
    ("€2.05", "two euros and five cents"),
    ("5 EUR", "five euros"),
    ("$2.5 million", "two point five million dollars"),
    ("-$5", "minus five dollars"),
    ("It costs $1,234.", "It costs one thousand two hundred thirty-four dollars."),
])
def test_currency(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("at 3:45", "at three forty-five"),
    ("at 3:05 pm", "at three oh five p m"),
    ("at 3:00", "at three o'clock"),
    ("at 14:30", "at fourteen thirty"),
    ("at 5 pm", "at five p m"),
    ("meet at 9:00 AM", "meet at nine a m"),
])
def test_time(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("1/2 cup", "one half cup"),
    ("3/4 of it", "three quarters of it"),
    ("2/3", "two thirds"),
    ("1/8", "one eighth"),
    ("available 24/7", "available twenty four seven"),
])
def test_fractions(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("e.g. this", "for example this"),
    ("E.g. this", "For example this"),
    ("Dr. Smith and Mr. Jones", "Doctor Smith and Mister Jones"),
    ("apples, pears, etc.", "apples, pears, et cetera."),
    ("apples, etc. Then", "apples, et cetera. Then"),
    ("apples, etc. then", "apples, et cetera then"),
    ("see fig. 3", "see figure three"),
    ("approx. 5 km", "approximately five kilometers"),
])
def test_abbreviations(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("2+3=5", "two plus three equals five"),
    ("2 + 3 = 5", "two plus three equals five"),
    ("5 - 3", "five minus three"),
    ("a × b", "a times b"),
    ("x² + y²", "x squared plus y squared"),
    ("x^2", "x squared"),
    ("x^10", "x to the power of ten"),
    ("a ≤ b", "a is less than or equal to b"),
    ("a < b", "a is less than b"),
    ("C++ is fun", "C++ is fun"),
    ("R&D", "R&D"),
    ("Tom & Jerry", "Tom and Jerry"),
])
def test_math_symbols(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("text", [
    "Run `pip install numpy==1.26` now",
    "```python\nx = 3 + 4\nprint(5 km)\n```",
    "See https://example.com/a/b?id=42&x=3.5 for details",
    "Mail me at john.doe42@example.com",
    "[docs](https://example.com/v1.2/page)",
])
def test_protected_spans_untouched(text):
    out = normalize(text)
    for span in ("`pip install numpy==1.26`", "x = 3 + 4", "https://example.com/a/b?id=42&x=3.5",
                 "john.doe42@example.com", "(https://example.com/v1.2/page)"):
        if span in text:
            assert span in out


def test_dollar_amounts_are_not_math():
    assert normalize("from $5 to $6") == "from five dollars to six dollars"


def test_plain_text_passes_through_unchanged():
    s = "Hello, world! This   has  odd spacing\n\n  and indentation."
    assert normalize(s) == s


def test_empty():
    assert normalize("") == ""
