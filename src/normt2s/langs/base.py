"""Language interface: everything that is *rules* (as opposed to dictionary data)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple


class Language:
    code = ""
    thousands_sep = ","
    decimal_sep = "."
    minus = "minus"
    point = "point"
    percent = "percent"
    range_word = "to"
    per_word = "per"
    currency_join = " and "
    # regex source for ordinal suffixes written after digits ("1st"); None = unsupported
    ordinal_suffix: Optional[str] = None
    # regex source for decade suffixes written after years ("1990s"); None = unsupported
    decade_suffix: Optional[str] = None
    # words that make a preceding 4-digit number read as a year
    year_prepositions: Tuple[str, ...] = ()
    # written scale words allowed after a currency amount ("$5 million")
    scale_words: Tuple[str, ...] = ()
    digit_words: Tuple[str, ...] = ()
    # words that give a following date its case ending (German "am 15.03."); a stream never
    # cuts right after them
    date_words: Tuple[str, ...] = ()
    # regex source for dates (None = unsupported); see :meth:`format_date`
    date_regex: Optional[str] = None
    # regex source for ordinal numbers written with a dot outside dates (None = unsupported)
    ordinal_dot_regex: Optional[str] = None

    def cardinal(self, n: int, gender: Optional[str] = None) -> str:
        raise NotImplementedError

    def ordinal(self, n: int) -> str:
        raise NotImplementedError

    def year(self, n: int) -> str:
        return self.cardinal(n)

    def decade(self, n: int) -> str:
        return self.cardinal(n)

    def time(self, hour: int, minute: int, suffix: Optional[str]) -> str:
        raise NotImplementedError

    def fraction(self, num: int, den: int) -> str:
        raise NotImplementedError

    def format_date(self, m, before: str) -> Optional[str]:
        """Spoken form of a ``date_regex`` match, or None to leave the text alone.

        ``before`` is the text preceding the match (German needs it for the case ending).
        """
        return None

    def format_ordinal_dot(self, m) -> str:
        """Spoken form of an ``ordinal_dot_regex`` match (the whole match is replaced)."""
        return m.group()

    def pluralize(self, singular: str) -> str:
        return singular

    def digits(self, s: str) -> str:
        return " ".join(self.digit_words[ord(c) - 48] for c in s)

    def currency(self, major: int, minor: Optional[int], cur) -> str:
        """Spoken amount for ``major.minor``; ``cur`` is a :class:`normt2s.lexicon.Currency`."""
        parts = []
        if major or not minor:
            parts.append(f"{self.cardinal(major, cur.major.gender)} {cur.major.pick(major == 1)}")
        if minor and cur.minor:
            parts.append(f"{self.cardinal(minor, cur.minor.gender)} {cur.minor.pick(minor == 1)}")
        return self.currency_join.join(parts)


_REGISTRY: Dict[str, Language] = {}


def register(lang: Language) -> None:
    _REGISTRY[lang.code] = lang


def get_language(code: str) -> Language:
    try:
        return _REGISTRY[code.lower().split("-")[0].split("_")[0]]
    except KeyError:
        raise ValueError(f"Unsupported language {code!r}; available: {sorted(_REGISTRY)}") from None
