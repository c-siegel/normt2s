import pytest

from normt2s import Normalizer


@pytest.fixture
def de():
    return Normalizer("de")


@pytest.mark.parametrize("src,want", [
    ("der 3. Platz", "der dritte Platz"),
    ("Der 3. Platz", "Der dritte Platz"),
    ("die 1. Runde", "die erste Runde"),
    ("das 2. Mal", "das zweite Mal"),
    ("den 3. Platz", "den dritten Platz"),
    ("am 2. Tag", "am zweiten Tag"),
    ("im 21. Jahrhundert", "im einundzwanzigsten Jahrhundert"),
    ("zum 7. Mal", "zum siebten Mal"),
    ("zur 8. Klasse", "zur achten Klasse"),
    ("beim 100. Versuch", "beim einhundertsten Versuch"),
    ("Kapitel 3. Danach", "Kapitel drei. Danach"),
    ("Es sind 3. Dann geht es", "Es sind drei. Dann geht es"),
    ("um 3. Mai", "um dritter Mai"),
    ("am 3. Mai", "am dritten Mai"),
    ("der 3. platz", "der drei. platz"),
    ("der 3.Platz", "der drei.Platz"),
    ("der 1234. Platz", "der eintausendzweihundertvierunddreißig. Platz"),
])
def test_ordinal_dot(de, src, want):
    assert de.normalize(src) == want


def test_english_unaffected():
    assert Normalizer("en").normalize("the 3. Place") == "the three. Place"


def test_stream_keeps_ordinal_with_its_noun(de):
    import random

    text = "Er wurde der 3. Platz. Beim 100. Versuch klappte es. Im 21. Jahrhundert ist das so.\nKapitel 3. Danach."
    want = de.normalize(text)
    for seed in range(60):
        rnd = random.Random(seed)
        s = de.stream()
        out, i = [], 0
        while i < len(text):
            k = rnd.randint(1, 6)
            out.append(s.feed(text[i:i + k]))
            i += k
        out.append(s.flush())
        assert "".join(out) == want, seed
