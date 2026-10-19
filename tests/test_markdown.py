import random
import time

import pytest

from normt2s import Normalizer


@pytest.fixture
def md():
    return Normalizer("en", markdown="strip")


@pytest.mark.parametrize("src,want", [
    ("**word** and __word__", "word and word"),
    ("*word* and _word_", "word and word"),
    ("~~word~~", "word"),
    ("## Title", "Title"),
    ("> quoted text", "quoted text"),
    ("> > nested", "nested"),
    ("- item\n* item\n+ item", "item\nitem\nitem"),
    ("1. step\n2) step", "step\nstep"),
    ("above\n---\nbelow", "above\n\nbelow"),
    ("***", ""),
    ("* * *", ""),
    ("___", ""),
    ("[text](https://example.com/a_b_c)", "text"),
    ("![alt text](pic.png)", "alt text"),
    ("`x = 1`", "x = 1"),
    ("```python\nx = 1 + 2\n```", "x = 1 + 2"),
    ("```\nraw 5 kg\n```", "raw 5 kg"),
    ("3*4*5", "three times four times five"),
    ("**3 * 4**", "three times four"),
    ("snake_case_name", "snake_case_name"),
    ("`a*b*c`", "a*b*c"),
    ("$a_1 * b_1$", "a sub one times b sub one"),
    ("**see `x_1`**", "see x_1"),
    ("*4* apples", "*four* apples"),
    ("***both***", "both"),
    ("**bold *and italic* text**", "bold and italic text"),
    ("2*(x+1)*3", "two times (x plus one) times three"),
    ("see https://example.com/a_b_c now", "see https://example.com/a_b_c now"),
    ("2 ** 3", "two ** three"),
])
def test_strip(md, src, want):
    assert md.normalize(src) == want


def test_keep_is_default():
    assert Normalizer("en").normalize("**word**") == "**word**"


def test_code_is_verbatim_even_with_numbers(md):
    assert md.normalize("Run `pip install numpy==1.26` for 5 min") == \
        "Run pip install numpy==1.26 for five minutes"


def test_invalid_mode():
    with pytest.raises(ValueError):
        Normalizer("en", markdown="html")


@pytest.mark.parametrize("ch", ["*", "_", "~", "`", "[", "#", ">", "-"])
def test_hostile(md, ch):
    text = ch * 10_000
    t = time.perf_counter()
    md.normalize(text)
    md.normalize((ch + "a ") * 5_000)
    assert time.perf_counter() - t < 1.0


DOC = (
    "# Title\n\nSome **bold** text, then _italic words_. Next: [a link](http://x.org/a_b) here.\n"
    "- first item costs $3.50\n- second *emphasis here* item\n1. step 1. One\n2) step two\n"
    "```python\nprint(1 + 2)\n```\n> A quote. With ~~struck text~~ inside.\n---\n"
    "Final 3*4*5 and `code 5` plus **bold. Spanning a sentence** end.\n"
)


def _chunks(text, rnd):
    i = 0
    while i < len(text):
        k = rnd.randint(1, 9)
        yield text[i:i + k]
        i += k


def test_stream_matches_whole(md):
    want = md.normalize(DOC)
    for seed in range(60):
        rnd = random.Random(seed)
        s = md.stream()
        out = "".join(s.feed(c) for c in _chunks(DOC, rnd)) + s.flush()
        assert out == want, seed
