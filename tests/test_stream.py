import pytest

from normt2s import Normalizer

SAMPLES = [
    ("en", "The train travels at 120 km/h. It left at 3:45 pm, e.g. on the 1st. Dr. Smith paid $3.50 for 2 kg of apples!\n"
           "Next line: 5 + 3 = 8, i.e. eight. In 1984 we had 1,234 visitors, etc. Then more text without a break"),
    ("en", "Run:\n```python\nx = 3 + 4\n```\nThen compute $x^2 + 1$ and 50% of 7.5 m. See https://a.b/c.d for 3 more."),
    ("de", "Der Zug fährt 120 km/h. Er kam um 14:30 an, z. B. am 3. Tag. Dr. Müller zahlte 3,50 € für 2 kg Äpfel.\n"
           "Im Jahr 1984 kamen 1.234 Besucher, usw. Danach noch mehr Text ohne Pause und mit 1/2 Liter"),
    ("en", "The area is $\\pi r^2$, so for $r = 3$ we get $\\frac{9\\pi}{1}$. Display:\n\\[ \\sum_{i=1}^{n} i = \\frac{n(n+1)}{2} \\]\n"
           "Due on March 3rd, 2024 at 5 pm. It costs $5 and $6."),
    ("de", "Die Fläche ist $\\pi r^2$. Abgabe am 15.03.2024 oder am 3. Mai. Dann $x \\in \\mathbb{R}$ mit 2,5 kg."),
]


@pytest.mark.parametrize("lang,text", SAMPLES)
@pytest.mark.parametrize("size", [1, 2, 3, 5, 8, 13, 50, 1000])
def test_streaming_matches_one_shot(lang, text, size):
    n = Normalizer(lang)
    chunks = [text[i:i + size] for i in range(0, len(text), size)]
    assert "".join(n.normalize_stream(chunks)) == n.normalize(text)


def test_emits_early_at_sentence_boundary():
    s = Normalizer("en").stream()
    assert s.feed("I have 5") == ""
    assert s.feed(" apples. ") == "I have five apples. "
    assert s.feed("And 2") == ""
    assert s.flush() == "And two"


def test_does_not_split_number_unit_or_abbreviation():
    s = Normalizer("en").stream()
    assert s.feed("Dr. ") == ""
    assert s.feed("Smith ran far. ") == "Doctor Smith ran far. "


def test_does_not_split_ordinal_dot_from_month():
    s = Normalizer("de").stream()
    assert s.feed("Abgabe am 3. ") == ""
    assert s.feed("Mai. ") == "Abgabe am dritten Mai. "


def test_waits_for_closing_code_fence():
    s = Normalizer("en").stream()
    assert s.feed("Intro.\n") == "Intro.\n"
    assert s.feed("```\nx = 1\n") == ""
    assert s.feed("y = 2\n") == ""
    assert s.feed("```\n") == "```\nx = 1\ny = 2\n```\n"


def test_long_run_without_boundary_flushes_but_not_after_a_number():
    s = Normalizer("en").stream(max_buffer=20)
    out = s.feed("one two three four five 5 ")
    assert out == "one two three four five "  # held back "5 " so a unit can still arrive
    assert s.feed("km next ") == ""  # nothing safe yet, still below max again
    assert s.flush() == "five kilometers next "
