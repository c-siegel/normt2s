from __future__ import annotations

from typing import Optional

from .base import Language, register

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
_SCALES = ("", "thousand", "million", "billion", "trillion", "quadrillion")
_MONTHS = ("January February March April May June July August September October November "
           "December").split()
_MONTH_RE = "|".join(_MONTHS)
_ORD_IRREGULAR = {"one": "first", "two": "second", "three": "third", "five": "fifth",
                  "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}


def _below_1000(n: int) -> str:
    parts = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        parts.append(_ONES[hundreds] + " hundred")
    if rest:
        if rest < 20:
            parts.append(_ONES[rest])
        else:
            tens, ones = divmod(rest, 10)
            parts.append(_TENS[tens] + ("-" + _ONES[ones] if ones else ""))
    return " ".join(parts)


class English(Language):
    code = "en"
    ordinal_suffix = r"st|nd|rd|th"
    decade_suffix = "s"
    year_prepositions = ("in", "since", "until", "till", "year", "circa", "ca.", "before",
                         "after", "during", "from", "between")
    scale_words = ("thousand", "million", "billion", "trillion")
    digit_words = tuple(_ONES[:10])
    date_regex = (
        r"(?<![\w.])(?:(?P<iy>\d{4})-(?P<im>\d{2})-(?P<id>\d{2})(?![\d-])"
        rf"|(?P<mn>{_MONTH_RE})\s(?:(?P<d>\d{{1,2}})(?:st|nd|rd|th)?(?!\d)"
        r"(?:,?\s(?P<y>\d{4})(?!\d))?|(?P<yo>\d{4})(?!\d)))"
    )

    def cardinal(self, n: int, gender: Optional[str] = None) -> str:
        if n < 0:
            return "minus " + self.cardinal(-n)
        if n == 0:
            return "zero"
        if n < 20:
            return _ONES[n]
        parts = []
        scale = 0
        while n:
            n, group = divmod(n, 1000)
            if group:
                words = _below_1000(group)
                parts.append(f"{words} {_SCALES[scale]}" if scale else words)
            scale += 1
        return " ".join(reversed(parts))

    def ordinal(self, n: int) -> str:
        words = self.cardinal(n)
        cut = max(words.rfind(" "), words.rfind("-")) + 1
        head, last = words[:cut], words[cut:]
        if last in _ORD_IRREGULAR:
            last = _ORD_IRREGULAR[last]
        elif last.endswith("y"):
            last = last[:-1] + "ieth"
        else:
            last += "th"
        return head + last

    def year(self, n: int) -> str:
        if not 1000 <= n <= 9999 or n % 1000 == 0 or 2000 < n < 2010:
            return self.cardinal(n)
        hi, lo = divmod(n, 100)
        if lo == 0:
            return f"{self.cardinal(hi)} hundred"
        if lo < 10:
            return f"{self.cardinal(hi)} oh {self.cardinal(lo)}"
        return f"{self.cardinal(hi)} {self.cardinal(lo)}"

    def format_date(self, m, before: str):
        if m.group("iy"):
            year, month, day = int(m.group("iy")), int(m.group("im")), int(m.group("id"))
            if not (1 <= month <= 12 and 1 <= day <= 31):
                return None
            return f"{_MONTHS[month - 1]} {self.ordinal(day)}, {self.year(year)}"
        month = m.group("mn")
        if m.group("yo"):
            return f"{month} {self.year(int(m.group('yo')))}"
        day = int(m.group("d"))
        if not 1 <= day <= 31:
            return None
        words = f"{month} {self.ordinal(day)}"
        return words + (f", {self.year(int(m.group('y')))}" if m.group("y") else "")

    def decade(self, n: int) -> str:
        words = self.year(n)
        return words[:-1] + "ies" if words.endswith("y") else words + "s"

    def time(self, hour: int, minute: int, suffix: Optional[str]) -> str:
        words = self.cardinal(hour)
        if minute == 0:
            if suffix:
                pass
            elif hour > 12 or hour == 0:
                words += " hundred"
            else:
                words += " o'clock"
        elif minute < 10:
            words += f" oh {self.cardinal(minute)}"
        else:
            words += f" {self.cardinal(minute)}"
        if suffix:
            words += " a m" if suffix[0] in "aA" else " p m"
        return words

    def fraction(self, num: int, den: int) -> str:
        top = self.cardinal(num)
        if den == 0:
            return f"{top} over zero"
        plural = num != 1
        if den == 2:
            return f"{top} {'halves' if plural else 'half'}"
        if den == 4:
            return f"{top} {'quarters' if plural else 'quarter'}"
        return f"{top} {self.ordinal(den)}{'s' if plural else ''}"

    def mixed_fraction(self, whole: int, num: int, den: int) -> str:
        frac = self.fraction(num, den)
        if num == 1:  # "one and a half", not "one and one half"
            frac = "a " + frac.split(" ", 1)[1]
        return f"{self.cardinal(whole)} and {frac}"

    def pluralize(self, singular: str) -> str:
        if singular.endswith(("s", "x", "z", "ch", "sh")):
            return singular + "es"
        if singular.endswith("y") and singular[-2:-1] not in "aeiou":
            return singular[:-1] + "ies"
        return singular + "s"


register(English())
