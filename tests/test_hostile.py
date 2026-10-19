"""Every public entry point must finish quickly on 100 kB of repeated hostile characters."""
import time

import pytest

from normt2s import Normalizer, Rule, RuleSet

PLAN_UNITS = ["*", "_", "{", "$", "\\", "`", "[", "::"]
EXTRA_UNITS = ["~", "(", "-", ".", "a", "\n", "<", "@", "]("]
SIZE = 100_000

RULES = RuleSet([Rule("a", "b"), Rule("{number} kg", "{number} kilograms"),
                 Rule("e. g.", "such as"), Rule("::", "colon")])


def _text(unit):
    return (unit * (SIZE // len(unit) + 1))[:SIZE]


@pytest.fixture(scope="module")
def normalizers():
    ns = [Normalizer("en"), Normalizer("de"), Normalizer("en", markdown="strip", latex_bare="speak")]
    for n in ns:
        n.normalize("warm up 1")
    return ns


@pytest.mark.parametrize("unit", PLAN_UNITS)
def test_normalize_is_fast(normalizers, unit):
    text = _text(unit)
    for n in normalizers:
        best = 9.0
        for _ in range(3):  # best of three keeps a busy machine from failing the test
            t = time.process_time()
            n.normalize(text)
            best = min(best, time.process_time() - t)
        assert best < 0.4, (unit, n.lang.code)  # about 0.1 s alone; margin for busy CI machines


@pytest.mark.parametrize("unit", PLAN_UNITS + EXTRA_UNITS)
def test_normalize_with_rules_and_extra_units(normalizers, unit):
    # a generous bound: this only catches super-linear behaviour, which takes seconds
    for n in normalizers:
        t = time.process_time()
        n.normalize(_text(unit))
        n.normalize(_text(unit), rules=RULES)
        assert time.process_time() - t < 2.0, (unit, n.lang.code)


@pytest.mark.parametrize("unit", PLAN_UNITS + EXTRA_UNITS)
def test_stream(normalizers, unit):
    text = _text(unit)
    s = normalizers[2].stream(rules=RULES)
    t = time.process_time()
    for i in range(0, len(text), 25_000):  # a few big feeds; every feed re-scans the buffer
        s.feed(text[i:i + 25_000])
    s.flush()
    assert time.process_time() - t < 8.0, unit
