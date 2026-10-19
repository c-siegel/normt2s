from __future__ import annotations

from typing import Optional

from .base import Language, register

_ONES = ("null eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf dreizehn "
         "vierzehn fünfzehn sechzehn siebzehn achtzehn neunzehn").split()
_TENS = "_ _ zwanzig dreißig vierzig fünfzig sechzig siebzig achtzig neunzig".split()
# (singular, plural) for scales >= million; all feminine
_SCALES = (None, None, ("Million", "Millionen"), ("Milliarde", "Milliarden"),
           ("Billion", "Billionen"), ("Billiarde", "Billiarden"))
_MONTHS = ("Januar Februar März April Mai Juni Juli August September Oktober November "
           "Dezember").split()
_MONTH_RE = "|".join(_MONTHS)
_DATIVE = {"am", "vom", "zum", "dem", "den", "des", "beim"}
_ORD_SMALL = {1: "erste", 3: "dritte", 7: "siebte", 8: "achte"}


def _below_100(n: int, final: bool) -> str:
    if n < 20:
        return "ein" if n == 1 and not final else _ONES[n]
    tens, ones = divmod(n, 10)
    if not ones:
        return _TENS[tens]
    return ("ein" if ones == 1 else _ONES[ones]) + "und" + _TENS[tens]


def _below_1000(n: int, final: bool) -> str:
    hundreds, rest = divmod(n, 100)
    out = ""
    if hundreds:
        out = ("ein" if hundreds == 1 else _ONES[hundreds]) + "hundert"
    if rest:
        out += _below_100(rest, final)
    return out


class German(Language):
    code = "de"
    thousands_sep = "."
    decimal_sep = ","
    point = "Komma"
    percent = "Prozent"
    range_word = "bis"
    per_word = "pro"
    currency_join = " "
    year_prepositions = ("im", "seit", "bis", "von", "ab", "vor", "nach", "um", "in", "jahr",
                         "jahre", "jahres", "ca.", "circa")
    scale_words = ("Tausend", "Million", "Millionen", "Milliarde", "Milliarden", "Billion",
                   "Billionen")
    digit_words = tuple(_ONES[:10])
    date_words = tuple(_DATIVE | {"der"})
    date_regex = (
        r"(?<![\w.])(?:(?P<iy>\d{4})-(?P<im>\d{2})-(?P<id>\d{2})(?![\d-])"
        r"|(?P<d>\d{1,2})\.(?:(?P<m>\d{1,2})\.(?:(?P<y>\d{4})(?!\d)|(?!\d))"
        rf"|\s(?P<mn>{_MONTH_RE})(?:\s(?P<yn>\d{{4}})(?!\d))?(?!\w))"
        rf"|(?P<mo>{_MONTH_RE})\s(?P<yo>\d{{4}})(?!\d))"
    )

    def cardinal(self, n: int, gender: Optional[str] = None) -> str:
        if n < 0:
            return "minus " + self.cardinal(-n, gender)
        if n == 0:
            return "null"
        groups = []
        m = n
        while m:
            m, g = divmod(m, 1000)
            groups.append(g)
        high = []
        low = ""
        for idx in range(len(groups) - 1, -1, -1):
            g = groups[idx]
            if not g:
                continue
            if idx == 0:
                low += _below_1000(g, True)
            elif idx == 1:
                low += _below_1000(g, False) + "tausend"
            else:
                sing, plur = _SCALES[idx]
                if g == 1:
                    high.append(f"eine {sing}")
                else:
                    words = _below_1000(g, False)
                    if words.endswith("ein"):
                        words += "e"
                    high.append(f"{words} {plur}")
        words = " ".join(high + ([low] if low else []))
        if gender and words.endswith("eins"):
            words = words[:-1] + ("e" if gender == "f" else "")
        return words

    def ordinal(self, n: int) -> str:
        if n == 0:
            return "nullte"
        rest = n % 100
        if 1 <= rest < 20:
            head = self.cardinal(n - rest) if n - rest else ""
            small = _ORD_SMALL.get(rest) or _ONES[rest] + "te"
            return head + small
        return self.cardinal(n) + "ste"

    def year(self, n: int) -> str:
        if 1100 <= n <= 1999 and n % 100:
            hi, lo = divmod(n, 100)
            return self.cardinal(hi) + "hundert" + (self.cardinal(lo) if lo else "")
        return self.cardinal(n)

    def format_date(self, m, before: str):
        if m.group("mo"):
            return f"{m.group('mo')} {self.year(int(m.group('yo')))}"
        if m.group("iy"):
            year, month, day = int(m.group("iy")), int(m.group("im")), int(m.group("id"))
        else:
            day = int(m.group("d"))
            month = int(m.group("m")) if m.group("m") else _MONTHS.index(m.group("mn")) + 1
            year = int(m.group("y") or m.group("yn") or 0) or None
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return None
        prev = (before.split() or [""])[-1].lower()
        ending = "en" if prev in _DATIVE else "e" if prev == "der" else "er"
        words = f"{self.ordinal(day)[:-1]}{ending} {_MONTHS[month - 1]}"
        return words + (f" {self.year(year)}" if year else "")

    def time(self, hour: int, minute: int, suffix: Optional[str]) -> str:
        words = f"{self.cardinal(hour, 'm')} Uhr"
        if minute:
            words += f" {self.cardinal(minute)}"
        return words

    def fraction(self, num: int, den: int) -> str:
        top = self.cardinal(num, "n")
        if den == 0:
            return f"{top} durch null"
        if den == 2:
            return f"{top} halb"
        # "dritte" -> "drittel", "fünfte" -> "fünftel"
        return f"{top} {self.ordinal(den)[:-1]}el"


register(German())
