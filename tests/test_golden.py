"""Golden files: one `input<TAB>expected` per line. Use \n for a newline in either column."""
from pathlib import Path

import pytest

from normt2s import Normalizer

GOLDEN = Path(__file__).parent / "golden"


def _cases(lang):
    for line in (GOLDEN / f"{lang}.tsv").read_text("utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            src, want = line.split("\t")
            yield src.replace("\n", "\n"), want.replace("\n", "\n")


@pytest.mark.parametrize("lang", ["en", "de"])
def test_golden(lang):
    n = Normalizer(lang)
    for src, want in _cases(lang):
        assert n.normalize(src) == want, src
