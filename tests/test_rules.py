import functools
import json
import random
import time

import pytest

from normt2s import Normalizer, Rule, RuleSet, normalize


def rs(*rules):
    return RuleSet(rules)


@pytest.fixture
def en():
    return Normalizer("en")


@pytest.fixture
def de():
    return Normalizer("de")


# ------------------------------------------------------------------ literal matching
def test_literal(en):
    assert en.normalize("the pH is low", rules=rs(Rule("pH", "p H"))) == "the p H is low"


def test_case(en):
    cs = rs(Rule("pH", "p H", case_sensitive=True))
    ci = rs(Rule("pH", "p H"))
    assert en.normalize("PH ph pH", rules=cs) == "PH ph p H"
    assert en.normalize("PH ph pH", rules=ci) == "p H p H p H"


def test_whole_word(en):
    r = rs(Rule("N", "newton", case_sensitive=True), Rule("kg", "kilos"))
    assert en.normalize("5 N and Newton", rules=r) == "five newton and Newton"
    assert en.normalize("10kg", rules=r) == "ten kilos"
    assert en.normalize("10kgs", rules=r) == "ten kgs"


def test_not_whole_word(en):
    assert en.normalize("Δt", rules=rs(Rule("Δ", "Delta", whole_word=False))) == "Delta t"


def test_digit_edge_guard(en):
    r = rs(Rule("3D", "three dee"))
    assert en.normalize("a 3D b 13D c 3Dx", rules=r) == "a three dee b thirteen D c three Dx"


def test_spaces_and_line_breaks(en):
    r = rs(Rule("e. g.", "such as"))
    assert en.normalize("one e.  g. two", rules=r) == "one such as two"
    assert en.normalize("one e.\ng. two", rules=r) == "one such as two"


def test_no_rematch_and_longest_first(en):
    r = rs(Rule("a", "b", whole_word=True), Rule("b", "a"), Rule("ab", "xy"), Rule("abc", "z"))
    assert en.normalize("a b ab abc", rules=r) == "b a xy z"


def test_ties_prefer_case_sensitive(en):
    r = rs(Rule("Ph", "case", case_sensitive=False), Rule("Ph", "exact", case_sensitive=True))
    assert en.normalize("Ph ph", rules=r) == "exact case"


def test_padding(en):
    assert en.normalize("xΔt", rules=rs(Rule("Δ", "Delta", whole_word=False))) == "x Delta t"


def test_rule_output_is_not_normalized_again(en):
    assert en.normalize("v2 now", rules=rs(Rule("v2", "version 2"))) == "version 2 now"


def test_empty_term_ignored(en):
    assert len(RuleSet([Rule("", "x"), Rule("a", "b")])) == 1


def test_deleting_rule(en):
    assert en.normalize("a [1] b", rules=rs(Rule("[1]", ""))) == "a  b"


# --------------------------------------------------------------------------- numbers
def test_number_formats(en, de):
    r = rs(Rule("{number} kg", "{number} kilograms"))
    assert en.normalize("5 kg", rules=r) == "five kilograms"
    assert en.normalize("1.5 kg", rules=r) == "one point five kilograms"
    assert en.normalize("1,234.5 kg", rules=r) == "one thousand two hundred thirty-four point five kilograms"
    assert en.normalize("1,5 kg", rules=r) == "one point five kilograms"
    rd = rs(Rule("{number} kg", "{number} Kilogramm"))
    assert de.normalize("3.000,25 kg", rules=rd) == "dreitausend Komma zwei fünf Kilogramm"
    assert de.normalize("1,5 kg", rules=rd) == "eins Komma fünf Kilogramm"


def test_two_numbers(en):
    r = rs(Rule("{number}x{number}", "{number} by {number}"))
    assert en.normalize("a 3x4 b", rules=r) == "a three by four b"


def test_negative_number(en):
    r = rs(Rule("{number} kg", "{number} kilograms"))
    assert en.normalize("-5 kg", rules=r) == "minus five kilograms"


def test_number_edge_guard(en):
    r = rs(Rule("{number} kg", "{number} kilograms"))
    assert en.normalize("x5 kg", rules=r) == "x5 kg"
    assert en.normalize("1 kg", rules=r) == "one kilogram"


def test_german_gender_via_lexicon_noun(de):
    r = rs(Rule("{number} kg", "{number} Kilogramm"), Rule("{number} min", "{number} Minute"))
    assert de.normalize("1 kg bei pH 7", rules=r) == "ein Kilogramm bei pH sieben"
    assert de.normalize("21 min", rules=r) == "einundzwanzig Minuten"
    assert de.normalize("1 min", rules=r) == "eine Minute"
    assert de.normalize("1,5 kg", rules=r) == "eins Komma fünf Kilogramm"


def test_explicit_gender_and_plural(de):
    r = rs(Rule("{number} Std.", "{number} Stunde", gender="f", plural="Stunden"))
    assert de.normalize("1 Std.", rules=r) == "eine Stunde"
    assert de.normalize("3 Std.", rules=r) == "drei Stunden"


def test_plan_example(de):
    rules = RuleSet([
        Rule("pH", "p H", case_sensitive=True),
        Rule("{number} kg", "{number} Kilogramm"),
        Rule("{number} Std.", "{number} Stunde", gender="f", plural="Stunden"),
        Rule("Δ", "Delta", whole_word=False),
    ])
    assert de.normalize("1 kg bei pH 7", rules=rules) == "ein Kilogramm bei p H sieben"


# ------------------------------------------------------------------ applied / helpers
def test_applied(en):
    a, b = Rule("pH", "p H"), Rule("ph2", "x")
    applied = []
    en.normalize("pH pH and ph2 and pH", rules=rs(a, b), applied=applied)
    assert applied == [a, b]


def test_hash_cache_and_equality():
    a = RuleSet([Rule("pH", "p H")])
    b = RuleSet([Rule("pH", "p H")])
    assert a == b and hash(a) == hash(b)
    calls = []

    @functools.lru_cache(maxsize=None)
    def get(rules):
        calls.append(1)
        return rules

    get(a), get(b)
    assert len(calls) == 1
    with pytest.raises(AttributeError):
        a.foo = 1


def test_from_dicts_and_camel_case(en):
    r = RuleSet.from_dicts([{"term": "pH", "spoken": "p H", "caseSensitive": True, "wholeWord": True}])
    assert r.rules[0].case_sensitive is True
    assert en.normalize("pH", rules=r) == "p H"


def test_load(tmp_path, en):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"rules": [{"term": "pH", "spoken": "p H"}]}), "utf-8")
    assert en.normalize("pH", rules=RuleSet.load(path)) == "p H"


@pytest.mark.parametrize("bad", [
    [{"term": "a"}],
    [{"term": "a", "spoken": "b", "nope": 1}],
    [{"term": 1, "spoken": "b"}],
    [{"term": "a", "spoken": "b", "whole_word": "yes"}],
    ["text"],
])
def test_from_dicts_invalid(bad):
    with pytest.raises(ValueError):
        RuleSet.from_dicts(bad)


def test_limits():
    with pytest.raises(ValueError):
        RuleSet([Rule("x" * 201, "y")])
    with pytest.raises(ValueError):
        RuleSet([Rule(f"t{i}", "y") for i in range(2001)])
    RuleSet([Rule("x" * 200, "y")])


def test_shared_normalizer_and_helper(en):
    r = rs(Rule("pH", "p H"))
    assert normalize("pH", "en", r) == "p H"
    assert en.lexicon.abbreviations.get("pH") is None
    assert en.normalize("pH") == "pH"


def test_ordinary_text_untouched_without_rules(en):
    assert en.normalize("5 kg", rules=RuleSet()) == "five kilograms"


# ------------------------------------------------------------------------- streaming
def test_stream_with_rules(en):
    r = rs(Rule("e. g.", "such as"), Rule("{number} Std.", "{number} hours"))
    text = "Use fruit, e. g. apples. It takes 3 Std. today. Then pH 7 follows.\nDone"
    want = en.normalize(text, rules=r)
    for seed in range(40):
        rnd = random.Random(seed)
        s = en.stream(rules=r)
        out, i = [], 0
        while i < len(text):
            k = rnd.randint(1, 7)
            out.append(s.feed(text[i:i + k]))
            i += k
        out.append(s.flush())
        assert "".join(out) == want, seed
    assert "".join(en.normalize_stream(iter(text), rules=r)) == want


# ----------------------------------------------------------------------------- speed
def test_200_rules_at_most_double():
    en = Normalizer("en")
    sentence = "The train travels at 120 km/h and left at 3:45 pm, i.e. in 1984 for $3.50. " * 3
    rnd = random.Random(7)
    rules = RuleSet([Rule("".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(7)), f"spoken {i}")
                     for i in range(200)])
    en.normalize(sentence, rules=rules)

    def bench(**kw):
        t = time.perf_counter()
        for _ in range(300):
            en.normalize(sentence, **kw)
        return time.perf_counter() - t

    base = min(bench() for _ in range(5))
    with_rules = min(bench(rules=rules) for _ in range(5))
    assert with_rules < base * 2.0, (with_rules, base)
