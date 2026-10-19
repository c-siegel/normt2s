import pytest

from normt2s import Normalizer


@pytest.mark.parametrize("src,want", [
    ("CO2", "C O two"),
    ("CO_2", "C O two"),
    ("H2O", "H two O"),
    ("CH4 and O3.", "C H four and O three."),
    ("C6H12O6", "C six H twelve O six"),
    ("H2SO4", "H two S O four"),
    ("ECO2000", "ECO2000"),
    ("CO23", "CO23"),
    ("U-235", "U two hundred thirty-five"),
    ("Pu-239", "P u two hundred thirty-nine"),
    ("A-4 paper", "A-four paper"),
])
def test_spelled(src, want):
    assert Normalizer("en").normalize(src) == want


def test_german_isotope():
    assert Normalizer("de").normalize("U-235") == "U zweihundertfünfunddreißig"


def test_add_spelled():
    n = Normalizer("en")
    assert n.normalize("ATP5") == "ATP5"
    n.add_spelled("ATP5")
    assert n.normalize("ATP5") == "A T P five"
    with pytest.raises(ValueError):
        n.add_spelled("a b")
