import json

import pytest

from normt2s import Normalizer


def fresh(lang="en"):
    return Normalizer(lang)


def test_add_abbreviation_and_capitalized_variant():
    n = fresh()
    assert n.normalize("ok LOLA") == "ok LOLA"
    n.add_abbreviation("LOLA", "Lola")
    assert n.normalize("ok LOLA") == "ok Lola"
    n.add_abbreviation("tbh", "to be honest")
    assert n.normalize("tbh yes. Tbh no") == "to be honest yes. To be honest no"


def test_add_abbreviation_no_capitalized_variant():
    n = fresh()
    n.add_abbreviation("pH", "p H", capitalized=False)
    assert n.normalize("pH 7 and PH") == "p H seven and PH"


def test_add_unit_default_plural_and_explicit():
    n = fresh()
    n.add_unit("kn", "knot")
    n.add_unit("ly", "light year")
    assert n.normalize("1 kn, 12 kn") == "one knot, twelve knots"
    assert n.normalize("3 ly") == "three light years"
    n.add_unit("ch", "child", "children")
    assert n.normalize("2 ch") == "two children"


@pytest.mark.parametrize("src,want", [
    ("10 µF", "zehn Mikrofarad"),
    ("10 μF", "zehn Mikrofarad"),            # Greek mu as well as the micro sign
    ("1013 hPa", "eintausenddreizehn Hektopascal"),
    ("1 mT", "ein Millitesla"),
    ("1 TWh", "eine Terawattstunde"),
    ("5 mmol/l", "fünf Millimol pro Liter"),
    ("1 km", "ein Kilometer"),
    ("5 Mm", "fünf Mm"),                     # only the prefixes listed for a base
    ("5F", "fünf F"),                        # a base given only for its prefixes is no unit
])
def test_german_prefixed_units(src, want):
    assert fresh("de").normalize(src) == want


def test_english_prefixed_units():
    n = fresh()
    assert n.normalize("10 µF and 1 MΩ") == "ten microfarads and one megaohm"
    assert n.normalize("13 TeV") == "thirteen teraelectron volts"


def test_add_prefixed_unit():
    n = fresh()
    n.add_unit("Np", "neper")
    n.add_prefixed_unit("Np", "dc")
    assert n.normalize("3 dNp") == "three decinepers"
    n.add_prefixed_unit("Wb", "m", "weber")
    assert n.normalize("2 mWb, 2 Wb") == "two milliwebers, two Wb"
    with pytest.raises(ValueError):
        n.add_prefixed_unit("xyz", "k")              # no such base and no singular
    with pytest.raises(ValueError):
        n.add_prefixed_unit("Np", "Q")               # no such prefix
    n.lexicon.add_prefix("Q", "quetta")
    n.add_prefixed_unit("Np", "Q")
    assert n.normalize("1 QNp") == "one quettaneper"


def test_explicit_units_win_over_generated():
    n = fresh()
    n.add_unit("km", "klick")
    n.add_prefixed_unit("m", "k")
    assert n.normalize("2 km") == "two klicks"


def test_add_currency():
    n = fresh()
    n.add_currency("CHF", ("franc", "francs"), ("rappen", "rappen"))
    assert n.normalize("5 CHF") == "five francs"
    assert n.normalize("5.20 CHF") == "five francs and twenty rappen"


def test_user_entries_override_builtin():
    n = fresh()
    n.add_abbreviation("Dr.", "Drive")
    assert n.normalize("Dr. Smith") == "Drive Smith"
    n.add_unit("m", "metre")
    assert n.normalize("2 m") == "two metres"


def test_remove():
    n = fresh()
    n.lexicon.remove("abbreviations", "vs.")
    assert n.normalize("a vs. b") == "a vs. b"


def test_changes_after_first_use_are_picked_up():
    n = fresh()
    assert n.normalize("5 kn") == "five kn"
    n.add_unit("kn", "knot")
    assert n.normalize("5 kn") == "five knots"


def test_load_json_file(tmp_path):
    f = tmp_path / "extra.json"
    f.write_text(json.dumps({
        "abbreviations": {"LMS": "learning management system", "N.B.": {"to": "note well", "final": False}},
        "units": {"kn": ["knot"], "Nm": ["newton meter"]},
    }), encoding="utf-8")
    n = fresh().load_lexicon(f)
    assert n.normalize("The LMS is 5 kn fast") == "The learning management system is five knots fast"
    assert n.normalize("2 Nm") == "two newton meters"


def test_german_unit_with_gender():
    n = fresh("de")
    n.add_unit("Std", "Stunde", "Stunden", "f")
    assert n.normalize("1 Std") == "eine Stunde"


def test_instances_do_not_share_state():
    a, b = fresh(), fresh()
    a.add_abbreviation("XYZ", "x y z")
    assert b.normalize("XYZ") == "XYZ"


def test_unknown_language():
    with pytest.raises(ValueError):
        Normalizer("xx")


def test_normalize_accepts_a_normalizer_instance():
    from normt2s import normalize

    n = Normalizer("de")
    n.lexicon.add_latex_command("cdot", "hehe")
    assert normalize(r"$a \cdot b$", n) == "a hehe b"
    # the shared per-language instance is a different object and keeps the default
    assert normalize(r"$a \cdot b$", "de") == "a mal b"


def test_add_latex_function_warns_when_a_command_shadows_it():
    n = Normalizer("en")
    with pytest.warns(UserWarning, match="add_latex_command"):
        n.lexicon.add_latex_function("cdot", "hehe")
    assert n.normalize(r"$a \cdot b$") == "a times b"  # the warning is accurate


def test_add_latex_function_without_conflict_does_not_warn():
    import warnings

    n = Normalizer("en")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        n.lexicon.add_latex_function("sinc", "sinc")


def test_builtin_data_has_no_command_function_overlap():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Normalizer("en")
        Normalizer("de")
