import pytest

from normt2s import Normalizer, normalize


def en(tex):
    return normalize(f"${tex}$", "en")


def de(tex):
    return normalize(f"${tex}$", "de")


@pytest.mark.parametrize("tex,expected", [
    ("x^2 + 3", "x squared plus three"),
    ("x^3", "x cubed"),
    ("x^4", "x to the fourth power"),
    ("x^{n}", "x to the power of n"),
    ("e^{-x}", "e to the power of minus x"),
    ("e^{x+1}", "e to the power of x plus one, end power"),
    ("x_1 + x_2", "x sub one plus x sub two"),
    ("a_{ij}", "a sub i j"),
    ("\\frac{1}{2}", "one half"),
    ("\\frac{3}{4}", "three quarters"),
    ("\\frac{a}{b}", "a over b"),
    ("\\frac{a+b}{c}", "the fraction a plus b over c, end fraction"),
    ("\\sqrt{x}", "square root of x"),
    ("\\sqrt{x+1}", "the square root of x plus one, end root"),
    ("\\sqrt[3]{8}", "cube root of eight"),
    ("\\sqrt[4]{x}", "fourth root of x"),
    ("3.14", "three point one four"),
    ("a \\neq b", "a is not equal to b"),
    ("a \\leq b \\leq c", "a is less than or equal to b is less than or equal to c"),
    ("x \\in \\mathbb{R}", "x is in the real numbers"),
    ("\\alpha + \\beta = \\gamma", "alpha plus beta equals gamma"),
    ("\\pi r^2", "pi r squared"),
    ("2 \\times 3 \\cdot 4", "two times three times four"),
    ("90^\\circ", "ninety degrees"),
    ("\\infty", "infinity"),
    ("n!", "n factorial"),
    ("f'(x)", "f prime of x"),
    ("f(x) = x^2", "f of x equals x squared"),
    ("\\sin(x)", "sine of x"),
    ("\\sin^2 x + \\cos^2 x = 1", "sine squared x plus cosine squared x equals one"),
    ("\\log_2 8", "log base two eight"),
    ("\\binom{n}{k}", "n choose k"),
    ("|x|", "absolute value of x"),
    ("|x - 1|", "the absolute value of x minus one, end absolute value"),
    ("\\left| x \\right|", "absolute value of x"),
    ("\\vec{v}", "vector v"),
    ("\\hat{x}", "x hat"),
    ("a, b, c", "a, b, c"),
    ("50\\%", "fifty percent"),
    ("5\\,\\mathrm{km}", "five kilometers"),
    ("1\\,\\text{km}", "one kilometer"),
    ("x \\text{ if } x > 0", "x if x is greater than zero"),
])
def test_english_latex(tex, expected):
    assert en(tex) == expected


@pytest.mark.parametrize("tex,expected", [
    ("\\sum_{i=1}^{n} i", "the sum from i equals one to n of i"),
    ("\\sum_{i=1}^{n} a_i", "the sum from i equals one to n of a sub i"),
    ("\\prod_{k=1}^{5} k", "the product from k equals one to five of k"),
    ("\\int_0^1 x^2 dx", "the integral from zero to one of x squared d x"),
    ("\\int f(x) dx", "the integral of f of x d x"),
    ("\\lim_{x \\to 0} \\frac{\\sin x}{x}", "the limit as x approaches zero of the fraction sine x over x, end fraction"),
    ("\\lim_{n \\to \\infty} a_n", "the limit as n approaches infinity of a sub n"),
])
def test_big_operators(tex, expected):
    assert en(tex) == expected


@pytest.mark.parametrize("tex,expected", [
    ("(x+1)^2", "open paren x plus one close paren squared"),
    ("(a+b)(c+d)", "open paren a plus b close paren open paren c plus d close paren"),
    ("2(x+1)", "two open paren x plus one close paren"),
    ("(x+1)", "x plus one"),
    ("y = (x+1)", "y equals x plus one"),
])
def test_parentheses_only_spoken_when_needed(tex, expected):
    assert en(tex) == expected


@pytest.mark.parametrize("tex,expected", [
    ("\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}",
     "the matrix, row one: a, b; row two: c, d, end matrix"),
    ("\\begin{cases} x & x > 0 \\\\ 0 & \\text{otherwise} \\end{cases}",
     "cases: x x is greater than zero; zero otherwise, end cases"),
    ("\\{ x \\mid x > 0 \\}", "the set x such that x is greater than zero"),
    ("\\{1, 2, 3\\}", "the set one, two, three"),
])
def test_environments_and_sets(tex, expected):
    assert en(tex) == expected


@pytest.mark.parametrize("text,expected", [
    (r"Solve \(x^2 = 4\) now", "Solve x squared equals four now"),
    (r"Display: \[ \frac{1}{2} \]", "Display: one half"),
    ("Euler: $$e^{i\\pi} + 1 = 0$$ done", "Euler: e to the power of i pi, end power plus one equals zero done"),
    ("The area is $\\pi r^2$.", "The area is pi r squared."),
    ("It costs $5 and $6 in total", "It costs five dollars and six dollars in total"),
])
def test_math_delimiters(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize("tex,expected", [
    ("x^2 + 3", "x zum Quadrat plus drei"),
    ("x^{n}", "x hoch n"),
    ("x^5", "x hoch fünf"),
    ("\\frac{1}{3}", "ein drittel"),
    ("\\frac{a+b}{c}", "der Bruch a plus b durch c, Ende Bruch"),
    ("\\sqrt{x}", "Wurzel aus x"),
    ("\\sqrt[3]{x}", "dritte Wurzel aus x"),
    ("a_1", "a Index eins"),
    ("3.14", "drei Komma eins vier"),
    ("3{,}14", "drei Komma eins vier"),
    ("a \\leq b", "a ist kleiner oder gleich b"),
    ("x \\in \\mathbb{R}", "x ist Element von den reellen Zahlen"),
    ("\\sum_{i=1}^{n} i", "die Summe von i gleich eins bis n über i"),
    ("\\int_0^1 f(x) dx", "das Integral von null bis eins über f von x d x"),
    ("\\lim_{x \\to 0} f(x)", "der Limes für x gegen null von f von x"),
    ("|x|", "Betrag von x"),
    ("n!", "n Fakultät"),
    ("5\\,\\mathrm{km}", "fünf Kilometer"),
])
def test_german_latex(tex, expected):
    assert de(tex) == expected


def test_latex_keep_mode_leaves_spans_untouched():
    n = Normalizer("en", latex="keep")
    text = r"Math $x^2 + 3$ and \[ \frac{1}{2} \] and \(a\) stay"
    assert n.normalize(text) == text


def test_malformed_latex_falls_back_to_original():
    out = normalize(r"Broken $\frac{1$ here")
    assert out.startswith("Broken ") and out.endswith(" here")


def test_unknown_command_is_spoken_by_name():
    assert en("\\foo + 1") == "foo plus one"


def test_user_can_extend_latex_vocabulary():
    n = Normalizer("en")
    n.lexicon.add_latex_command("R", "the reals")
    n.lexicon.add_latex_command("\\ohm", "ohms")
    n.lexicon.add_latex_function("sinc", "sinc")
    n.lexicon.add_phrase("frac", "{a} divided by {b}")
    assert n.normalize(r"$\R$") == "the reals"
    assert n.normalize(r"$5 \ohm$") == "five ohms"
    assert n.normalize(r"$\sinc(x)$") == "sinc of x"
    assert n.normalize(r"$\frac{a}{b}$") == "a divided by b"


def test_fuzz_never_raises():
    import random

    rnd = random.Random(1234)
    alphabet = list(r"\{}()[]^_&|$ abcxyz0123456789.,!'=+-/") + [
        r"\frac", r"\sqrt", r"\left", r"\right", r"\begin{pmatrix}", r"\end{pmatrix}", r"\sum",
        r"\int", r"\lim", r"\text{", r"\\", r"\mathbb{R}", r"\alpha", r"\unknown"]
    n = Normalizer("en")
    for _ in range(3000):
        junk = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(1, 25)))
        n.normalize(f"${junk}$ and \({junk}\)")
