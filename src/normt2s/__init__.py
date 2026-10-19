"""normt2s - lightweight text normalization for TTS (numbers, units, abbreviations)."""

from __future__ import annotations

from typing import Dict, Optional, Union

from .lexicon import Lexicon
from .normalizer import Normalizer
from .rules import Rule, RuleSet
from .stream import StreamNormalizer

__all__ = ["Normalizer", "Lexicon", "StreamNormalizer", "Rule", "RuleSet", "normalize",
           "get_normalizer"]
__version__ = "0.1.0"

_cache: Dict[str, Normalizer] = {}


def get_normalizer(lang: str = "en") -> Normalizer:
    """Shared per-language instance; add words to it and every ``normalize()`` call sees them."""
    n = _cache.get(lang)
    if n is None:
        n = _cache[lang] = Normalizer(lang)
    return n


def normalize(text: str, lang: Union[str, Normalizer] = "en", rules: Optional[RuleSet] = None) -> str:
    """Normalize ``text``.

    ``lang`` is a language code (uses the shared instance from :func:`get_normalizer`) or your
    own :class:`Normalizer`, so words added to it are honoured:
    ``normalize(text, my_normalizer)``. A plain ``Normalizer("de")`` you created yourself is a
    *separate* instance and is not seen by ``normalize(text, "de")``.
    """
    n = lang if isinstance(lang, Normalizer) else get_normalizer(lang)
    return n.normalize(text, rules)
