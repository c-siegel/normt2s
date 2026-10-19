import pytest

from normt2s import Normalizer


@pytest.fixture
def protect():
    return Normalizer("en")


@pytest.fixture
def speak():
    return Normalizer("en", latex_bare="speak")


@pytest.mark.parametrize("src,want", [
    (r"a \cdot b", "a times b"),
    (r"\frac{1}{2} is a half", "one half is a half"),
    (r"\sqrt{x+1} and more", "the square root of x plus one, end root and more"),
    (r"x = \pi r^2.", "x = pi r squared."),
    (r"C:\Users\name", r"C:\Users\name"),
    (r"\unknown{1}", r"\unknown{1}"),
    (r"\frac{1}{2", r"\frac{1}{2"),
])
def test_speak(speak, src, want):
    assert speak.normalize(src) == want


@pytest.mark.parametrize("src,want", [
    (r"\frac{1}{2} is a half", r"\frac{1}{2} is a half"),
    (r"\sqrt{x+1} and 5 more", r"\sqrt{x+1} and five more"),
    (r"x = \pi r^2.", r"x = \pi r^2."),
    (r"\unknown{1}", r"\unknown{1}"),
    (r"\frac{1}{2", r"\frac{1}{2"),
    (r"a \cdot b", r"a \cdot b"),
])
def test_protect(protect, src, want):
    assert protect.normalize(src) == want


def test_invalid_mode():
    with pytest.raises(ValueError):
        Normalizer("en", latex_bare="no")


def test_delimited_math_unchanged(protect):
    assert protect.normalize(r"Area $\pi r^2$ is 5") == "Area pi r squared is five"
