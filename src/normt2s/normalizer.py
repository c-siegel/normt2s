"""Single-pass, regex-driven normalizer.

Pipeline per unprotected segment:  abbreviations -> pre-symbols -> numbers/units -> post-symbols.
Regexes are compiled lazily and recompiled only when the lexicon changes.
"""

from __future__ import annotations

import functools
import re
import threading
from pathlib import Path
from typing import Any, Iterable, Iterator, NamedTuple, Optional, Sequence, Union

from .langs import Language, get_language
from . import markdown as _md
from .latex import LatexSpeaker, find_bare
from .lexicon import Lexicon
from .rules import NUMBER, Rule, RuleSet

_PROTECT = (
    r"(?s:```.*?```)"
    r"|`[^`\n]+`"
    r"|\uE000\d+\uE001"
    r"|\]\([^)\s]{0,300}\)"
    r"|https?://[^\s<>\"]*[^\s<>\".,;:!?)\]]"
    r"|www\.[^\s<>\"]*[^\s<>\".,;:!?)\]]"
    r"|(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    r"|</?[A-Za-z][^<>\n]*>"
)
# pandoc rule for single dollars: "$x^2$" is math, "$5 and $6" is not
_MATH = (
    r"(?s:\$\$(?P<m1>.*?)\$\$)"
    r"|(?s:\\\[(?P<m2>.*?)\\\])"
    r"|(?s:\\\((?P<m3>.*?)\\\))"
    r"|(?<![\w$])\$(?![\s$])(?P<m4>[^$\n]*?)(?<![\s\\])\$(?!\d)"
)
# Code, URLs, e-mail addresses, HTML tags and link targets: never touched.
PROTECT_RE = re.compile(_PROTECT)
# The above plus LaTeX math spans (spoken or kept, see ``Normalizer(latex=...)``).
SPAN_RE = re.compile(_PROTECT + "|" + _MATH)



class _Compiled(NamedTuple):
    """Everything derived from the lexicon; replaced as one object so readers never see half."""

    version: int
    abbr: Any
    abbr_re: Any
    no_boundary_tokens: Any
    sym: Any
    ops: Any
    pre_re: Any
    dot_re: Any
    post_re: Any
    let_re: Any
    token_re: Any
    suffix_re: Any
    scale_re: Any
    year_re: Any
    range_re: Any
    date_re: Any
    ord_dot_re: Any
    punct_re: Any
    punct: Any
    spelled_re: Any
    iso_re: Any
    span_re: Any
    protected: Any
    openers: Any


# vulgar fractions, alone or after a whole number: "½", "1½", "2 ¾"
_VULGAR = {"½": (1, 2), "¼": (1, 4), "¾": (3, 4)}
_VULGAR_RE = re.compile(r"(?<![\d.,])(?:(\d{1,6}) ?)?([½¼¾])")
# Greek letters (and µ) next to another one form a Greek word, which is left alone
_GREEK = "\u0370-\u03FF\u1F00-\u1FFFµ"

# Rule output is parked behind placeholders (no digits, no word characters) during the pipeline.
_RULE_PH = re.compile("\uE002([\uE100-\uE1FF]+)\uE003")


def _encode(n: int) -> str:
    digits = []
    while True:
        n, d = divmod(n, 256)
        digits.append(chr(0xE100 + d))
        if not n:
            return "\uE002" + "".join(reversed(digits)) + "\uE003"


def _decode(s: str) -> int:
    n = 0
    for ch in s:
        n = n * 256 + ord(ch) - 0xE100
    return n


@functools.lru_cache(maxsize=None)
def _time_word_re(word: str):
    return re.compile(r"\s?" + re.escape(word) + r"(?!\w)")


_NEXT_WORD = re.compile(r" ([^\W\d_][\w-]*)")
_DIGIT_RE = re.compile(r"\d")
_MAX_INT_DIGITS = 15
_NBSP = "\u00a0\u202f"


_EMPTY = _Compiled(-1, *([None] * 23))


class Normalizer:
    """Turn written text into text that is safe to hand to a TTS engine.

    >>> Normalizer("en").normalize("It costs $3.50 for 2 kg, e.g. in 1984.")
    'It costs three dollars and fifty cents for two kilograms, for example in nineteen eighty-four.'
    """

    def __init__(self, lang: Union[str, Language] = "en", lexicon: Optional[Lexicon] = None,
                 latex: str = "speak", latex_bare: str = "protect", markdown: str = "keep"):
        """``latex="speak"`` reads math aloud, ``latex="keep"`` leaves LaTeX spans untouched.

        ``latex_bare`` is about LaTeX outside math delimiters (``a \\cdot b``): ``"protect"``
        leaves it untouched, ``"speak"`` reads it like delimited math.

        ``markdown="strip"`` removes Markdown markers (``**``, ``#``, list bullets, links, ...)
        before normalizing; ``"keep"`` (default) leaves the text as it is.
        """
        if latex not in ("speak", "keep"):
            raise ValueError("latex must be 'speak' or 'keep'")
        if latex_bare not in ("protect", "speak"):
            raise ValueError("latex_bare must be 'protect' or 'speak'")
        if markdown not in ("keep", "strip"):
            raise ValueError("markdown must be 'keep' or 'strip'")
        self._markdown = markdown == "strip"
        self._bare_speak = latex_bare == "speak"
        self.lang = get_language(lang) if isinstance(lang, str) else lang
        self.lexicon = lexicon or Lexicon.builtin(self.lang)
        self._latex = LatexSpeaker(self) if latex == "speak" else None
        self._bare = self._latex or (LatexSpeaker(self) if self._bare_speak else None)
        self._lock = threading.Lock()
        self._c = _EMPTY

    # ------------------------------------------------------------ dictionary API
    def add_abbreviation(self, key: str, to: str, **kw) -> "Normalizer":
        self.lexicon.add_abbreviation(key, to, **kw)
        return self

    def add_unit(self, symbol: str, singular: str, plural: Optional[str] = None,
                 gender: Optional[str] = None) -> "Normalizer":
        self.lexicon.add_unit(symbol, singular, plural, gender)
        return self

    def add_prefixed_unit(self, base: str, prefixes: str, singular: Optional[str] = None,
                          plural: Optional[str] = None, gender: Optional[str] = None) -> "Normalizer":
        self.lexicon.add_prefixed_unit(base, prefixes, singular, plural, gender)
        return self

    def add_currency(self, symbol: str, major: Sequence, minor: Optional[Sequence] = None):
        self.lexicon.add_currency(symbol, major, minor)
        return self

    def add_symbol(self, key: str, word: str) -> "Normalizer":
        self.lexicon.add_symbol(key, word)
        return self

    def add_spelled(self, token: str) -> "Normalizer":
        self.lexicon.add_spelled(token)
        return self

    def add_protected(self, pattern: str, spoken: Optional[str] = None,
                      opener: Optional[str] = None) -> "Normalizer":
        self.lexicon.add_protected(pattern, spoken, opener)
        return self

    def add_punctuation(self, char: str, replacement: str) -> "Normalizer":
        self.lexicon.add_punctuation(char, replacement)
        return self

    def load_lexicon(self, path: Union[str, Path]) -> "Normalizer":
        self.lexicon.load(path)
        return self

    # --------------------------------------------------------------- public API
    def normalize(self, text: str, rules: Optional[RuleSet] = None,
                  applied: Optional[list] = None, *, _mid_line: bool = False) -> str:
        """Normalize ``text``. ``rules`` is an optional :class:`~normt2s.rules.RuleSet`; every
        rule that matched is appended once to ``applied`` (a list) in order of first match."""
        if not text:
            return text
        c = self.ensure_compiled()
        if not self._markdown:
            return self._run(text, c, rules, applied)
        text, verbatim = _md.strip(text, c.span_re, _mid_line)
        return _md.restore(self._run(text, c, rules, applied), verbatim)

    def _run(self, text: str, c: _Compiled, rules: Optional[RuleSet] = None,
             applied: Optional[list] = None) -> str:
        out = []
        pos = 0
        closing = ".,;:!?)"
        for m in c.span_re.finditer(text):
            start = m.start()
            if start > pos:
                out.append(self._gap(text[pos:start], c, rules, applied))
            spoken = None
            kind = m.lastgroup
            if kind is not None and kind[0] == "p":  # an application's protected pattern
                spoken = c.protected[int(kind[1:])]
                if spoken == "":  # removed: close the gap it leaves
                    if text[m.end():m.end() + 1] in closing and out and out[-1][-1:] == " ":
                        out[-1] = out[-1].rstrip(" ")
                    nxt = m.end()
                    if text[nxt:nxt + 1] == " " and (not out or out[-1][-1:].isspace()):
                        nxt += 1
                    pos = nxt
                    continue
            elif self._latex is not None and kind in ("m1", "m2", "m3", "m4"):
                spoken = self._latex.speak(m.group(kind))
            out.append(m.group() if spoken is None else spoken)
            pos = m.end()
        if pos == 0:
            return self._gap(text, c, rules, applied)
        if pos < len(text):
            out.append(self._gap(text[pos:], c, rules, applied))
        return "".join(out)

    __call__ = normalize

    def stream(self, max_buffer: int = 400, *, first_min_chars: int = 0, min_chars: int = 0,
               rules: Optional[RuleSet] = None):
        """A stateful wrapper for token-by-token LLM output, see :class:`StreamNormalizer`.

        ``first_min_chars`` releases the first chunk at the first boundary at least that long
        (early audio); ``min_chars`` makes later chunks at least that long. 0 (default) keeps
        the behaviour of releasing everything up to the last boundary as soon as possible.
        """
        from .stream import StreamNormalizer

        return StreamNormalizer(self, max_buffer, rules=rules, first_min_chars=first_min_chars,
                                min_chars=min_chars)

    def normalize_stream(self, chunks: Iterable[str], max_buffer: int = 400, *,
                         first_min_chars: int = 0, min_chars: int = 0,
                         rules: Optional[RuleSet] = None) -> Iterator[str]:
        s = self.stream(max_buffer, first_min_chars=first_min_chars, min_chars=min_chars,
                        rules=rules)
        for chunk in chunks:
            for piece in s.feed_pieces(chunk):
                if piece.spoken:
                    yield piece.spoken
        last = s.flush_piece()
        if last is not None and last.spoken:
            yield last.spoken

    def _gap(self, text: str, c: _Compiled, rules: Optional[RuleSet] = None,
             applied: Optional[list] = None) -> str:
        """Text between protected spans: bare LaTeX runs are kept (or spoken), the rest normalized."""
        runs = find_bare(text, self.lexicon) if "\\" in text else ()
        if not runs:
            return self._plain(text, c, rules, applied)
        out, pos = [], 0
        for start, end, speakable in runs:
            if start > pos:
                out.append(self._plain(text[pos:start], c, rules, applied))
            spoken = None
            if speakable and self._bare_speak:
                spoken = self._bare.speak(text[start:end])
            if spoken is None:
                out.append(text[start:end])
            else:
                if out and out[-1][-1:].isalnum():
                    out.append(" ")
                out.append(spoken)
                if text[end:end + 1].isalnum():
                    out.append(" ")
            pos = end
        if pos < len(text):
            out.append(self._plain(text[pos:], c, rules, applied))
        return "".join(out)

    # ------------------------------------------------------------- compilation
    def ensure_compiled(self) -> _Compiled:
        """The current compiled state; rebuilt (once, under a lock) after lexicon changes."""
        c = self._c
        if c.version != self.lexicon.version:
            with self._lock:
                c = self._c
                if c.version != self.lexicon.version:
                    c = self._c = self._compile()
        return c

    @property
    def no_boundary_tokens(self):
        return self._c.no_boundary_tokens

    def _compile(self) -> _Compiled:
        lang, lex = self.lang, self.lexicon
        esc = re.escape
        with lex.lock:
            version = lex.version
            snap = lex.snapshot()
        return self._build(lang, snap, version, esc)

    def _build(self, lang, lex, version, esc) -> _Compiled:

        # abbreviations: whitespace inside keys is optional ("z. B." matches "z.B.")
        abbr = {re.sub(r"\s+", "", k): v for k, v in lex.abbreviations.items()}
        keys = sorted(lex.abbreviations, key=len, reverse=True)
        abbr_re = re.compile(
            r"(?<![\w.])(?:" + "|".join(r"\s*".join(esc(p) for p in k.split()) for k in keys)
            + r")(?!\w)") if keys else None
        # tokens after which a "." does NOT end a sentence (used by the stream splitter)
        no_boundary = set()
        for k in keys:
            toks = k.split()
            no_boundary.update(toks[:-1])
            if toks[-1].endswith("."):
                no_boundary.add(toks[-1])

        # symbols that need digit context are handled before the number pass
        sym = lex.symbols
        ops = lex.operators
        pre_alts = [
            r"(?<=\d) [-−] (?=\d)",         # 5 - 3
            r"\^(?P<exp>-?\w+)",             # x^2
            r"#(?=\d)",                      # #5
            r"(?<![\w+])\+(?=\d)",           # +49
        ]
        if "*" in ops:                       # 3 * 4, 3*4, 2*(x+1); never *word* or **
            pre_alts.append(r"(?<=[\d)\]])\s*(?P<mul>\*)\s*(?=[\d(\[])")
        if "/" in ops:                       # 3 / 4 with spaces; 1/2 stays a fraction
            pre_alts.append(r"(?<=[\d)\]]) (?P<div>/) (?=[\d(\[])")
        pre_re = re.compile("|".join(pre_alts))
        # 2 · 3, m · a; never Lehrer·innen or "Home · About". Its own regex, run only on text with
        # a "·": its leading lookbehinds would otherwise be tried at every letter.
        letter = r"[^\W\d_]"
        dot_re = re.compile(rf"(?:(?<=[\d)\]])|(?<=(?<!{letter}){letter}))\s*·\s*"
                            rf"(?=[\d(\[]|{letter}(?!{letter}))") if "·" in ops else None
        # every other single-character symbol is infix; longer keys (``!=``) go by length
        handled = "-^#%=+<>&²³"
        chars = [k for k in sym if len(k) == 1 and not k.isalnum() and k not in handled]
        multi = sorted((k for k in sym if len(k) > 1 and k[0] != "^"), key=len, reverse=True)
        # letters (Greek, ℏ): "Δt" is "Delta t"; µ only when no letter follows ("µm" is a unit)
        alpha = [k for k in sym if len(k) == 1 and k.isalpha()]
        greek = "".join(esc(k) for k in alpha if re.match(f"[{_GREEK}]", k) and k not in "µμ")
        micro = "".join(esc(k) for k in alpha if k in "µμ")
        other = "".join(esc(k) for k in alpha if not re.match(f"[{_GREEK}]", k))
        # the letter comes first so the lookarounds only run on a match: (?<![Greek].) checks the
        # character before it
        let_alts = ([rf"[{greek}](?<![{_GREEK}].)(?![{_GREEK}])"] if greek else []) \
            + ([rf"[{micro}](?<![{_GREEK}].)(?![{_GREEK}]|[^\W\d_])"] if micro else []) \
            + ([f"[{other}]"] if other else [])
        post_re = re.compile(
            r"(?P<sq>(?<=[\w)\]])[²³])"
            + (r"|\s?(?P<mop>" + "|".join(esc(k) for k in multi) + r")\s?" if multi else "")
            + (r"|\s?(?P<op>[" + "".join(esc(k) for k in chars) + r"])\s?" if chars else "")
            # a parked rule output (\uE002...\uE003) is an operand too: "F = 1 N"
            + r"|(?<=[\w)\]\uE003])\s?(?P<eq>[=+])\s?(?=[\w(\[$€£\uE002-])"
            r"|(?<=\S) (?P<cmp>[<>]) (?=\S)"
            r"|(?<=\s)(?P<amp>&)(?=\s)"
        )
        # its own regex, run only on non-ASCII text: as a branch of post_re it slowed every position
        let_re = re.compile("|".join(let_alts)) if let_alts else None

        # numbers
        ts, ds = esc(lang.thousands_sep), esc(lang.decimal_sep)
        guard = r"(?!\.\d)" if lang.decimal_sep == "." else ""
        thous = rf"\d{{1,3}}(?:(?:{ts}|[ {_NBSP}])\d{{3}})+(?!\d)(?:{ds}\d+)?"
        ver = r"\d+(?:\.\d+){2,}"
        plain = rf"\d+(?:{ds}\d+)?{guard}"
        cur_chars = "".join(esc(c) for c in lex.currencies if len(c) == 1)
        cur_pre = rf"(?:(?P<cur>[{cur_chars}])\s?)?" if cur_chars else ""
        token_re = re.compile(
            r"(?<![\w.])" + (rf"(?P<neg0>[-−](?=[{cur_chars}]))?" if cur_chars else "")
            + cur_pre + r"(?P<neg>[-−](?=\d))?"
            r"(?:(?P<frac>\d{1,3}/\d{1,3})(?![\w/]|\.\d)"
            r"|(?P<time>(?P<hh>\d{1,2}):(?P<mm>[0-5]\d))(?![\d:])"
            rf"|(?P<num>(?P<th>{thous})|(?P<ver>{ver})|{plain}))"
        )

        # what may follow a number
        syms = sorted(lex.units, key=len, reverse=True)
        # a lone Latin capital is a unit only attached to the number: "12V", but "Klasse 5 A"
        free = "|".join(esc(s) for s in syms if not (len(s) == 1 and s.isupper() and s.isascii()))
        attached = "|".join(esc(s) for s in syms if len(s) == 1 and s.isupper() and s.isascii())
        every = "|".join(esc(s) for s in syms)
        alts = [r"(?P<pct>\s?%)"]
        if lang.ordinal_suffix:
            alts.append(rf"(?P<ord>(?:{lang.ordinal_suffix})(?![A-Za-z]))")
        if lang.decade_suffix:
            alts.append(rf"(?P<dec>{lang.decade_suffix}(?![A-Za-z]))")
        alts.append(r"(?P<ampm>\s?(?:[ap]\.?m\.?|[AP]M)(?![A-Za-z]))")
        cur_all = "|".join(esc(c) for c in sorted(lex.currencies, key=len, reverse=True))
        if cur_all:
            alts.append(rf"(?P<csuf>\s?(?P<csym>{cur_all})(?![\w]))")
        alts.append(
            rf"(?P<unit>(?:[ {_NBSP}]?(?P<uf>{free or '(?!)'})|(?P<ua>{attached or '(?!)'}))"
            rf"(?:/(?P<den>{every or '(?!)'}))?(?![\w]))"
        )
        suffix_re = re.compile("|".join(alts))
        scale_re = re.compile(
            r"\s(?P<scale>" + "|".join(lang.scale_words) + r")(?![A-Za-z])", re.I
        ) if lang.scale_words else None
        year_re = re.compile(
            r"(?:^|[\s(])(?:" + "|".join(esc(p) for p in lang.year_prepositions) + r")\s+$", re.I
        ) if lang.year_prepositions else None
        range_re = re.compile(r"(?<=\d)\s?[–—]\s?(?=\d)")
        punct_re = re.compile(
            r"[ 	]*(?P<p>[" + "".join(esc(k) for k in lex.punctuation) + r"])[ 	]*"
        ) if lex.punctuation else None
        def spelled_key(k: str) -> str:
            return "".join(r"_?\d" if ch.isdigit() else esc(ch) for ch in k)

        spelled_re = re.compile(
            r"(?<!\w)(?:" + "|".join(spelled_key(k) for k in sorted(lex.spelled, key=len, reverse=True))
            + r")(?!\w)") if lex.spelled else None
        elements = "|".join(sorted(Lexicon.elements(), key=len, reverse=True))
        # "m" marks a metastable isotope: "Tc-99m"
        iso_re = re.compile(rf"(?<![\w-])(?P<el>{elements})-(?P<n>\d{{1,3}})(?P<meta>m?)(?![\w-])")
        if lex.protected:
            custom = "|".join(f"(?P<p{i}>(?:{pat}))" for i, pat in enumerate(lex.protected))
            span_re = re.compile(custom + "|" + _PROTECT + "|" + _MATH)
        else:
            span_re = SPAN_RE
        date_re = re.compile(lang.date_regex) if lang.date_regex else None
        ord_dot_re = re.compile(lang.ordinal_dot_regex) if lang.ordinal_dot_regex else None
        return _Compiled(version, abbr, abbr_re, no_boundary, sym, ops, pre_re, dot_re, post_re,
                         let_re, token_re, suffix_re, scale_re, year_re, range_re, date_re,
                         ord_dot_re, punct_re, dict(lex.punctuation),
                         spelled_re, iso_re, span_re, tuple(spoken for spoken, _ in lex.protected.values()),
                         tuple(op for _, op in lex.protected.values() if op))

    # ---------------------------------------------------------------- pipeline
    def _plain(self, text: str, c: Optional[_Compiled] = None, rules: Optional[RuleSet] = None,
               applied: Optional[list] = None) -> str:
        c = c or self.ensure_compiled()
        if rules is None or not rules.rules:
            return self._plain_core(text, c)
        spoken: list = []
        text = self._apply_rules(text, rules, applied, spoken, c)
        text = self._plain_core(text, c)
        return _RULE_PH.sub(lambda m: spoken[_decode(m.group(1))], text) if spoken else text

    def _plain_core(self, text: str, c: _Compiled) -> str:
        if _DIGIT_RE.search(text):
            if c.spelled_re:
                text = c.spelled_re.sub(self._spelled_sub, text)
            text = c.iso_re.sub(self._isotope_sub, text)
        if c.abbr_re:
            text = c.abbr_re.sub(lambda m: self._abbr_sub(m, c), text)
        has_digit = _DIGIT_RE.search(text) is not None
        if has_digit and c.date_re:
            text = c.date_re.sub(self._date_sub, text)
        if has_digit and c.ord_dot_re:
            text = c.ord_dot_re.sub(self.lang.format_ordinal_dot, text)
        if "½" in text or "¼" in text or "¾" in text:
            text = _VULGAR_RE.sub(self._vulgar_sub, text)
        if c.dot_re is not None and "·" in text:
            text = c.dot_re.sub(f" {c.ops['·']} ", text)
        text = c.pre_re.sub(lambda m: self._pre_sub(m, c), text)
        if has_digit:
            text = c.range_re.sub(f" {self.lang.range_word} ", text)
            text = self._numbers(text, c)
        if c.punct_re:
            text = c.punct_re.sub(lambda m: self._punct_sub(m, c), text)
        text = c.post_re.sub(lambda m: self._post_sub(m, c), text)
        if c.let_re is not None and not text.isascii():
            text = c.let_re.sub(lambda m: self._let_sub(m, c), text)
        return text

    # ------------------------------------------------------------------- rule sets
    def _apply_rules(self, text: str, rules: RuleSet, applied: Optional[list], spoken: list,
                     c: _Compiled) -> str:
        """Replace rule matches by placeholders; their final text is stored in ``spoken``."""
        out, pos = [], 0
        for m, rule in rules.scan(text):
            words = self._rule_words(rule, m)
            if words is None:  # a number that cannot be parsed: leave it to the normal pipeline
                continue
            if rule.renormalize:
                words = self._plain_core(words, c)
            if applied is not None and rule not in applied:
                applied.append(rule)
            start, end = m.start(), m.end()
            if words[:1].isalnum() and text[start - 1:start].isalnum():
                words = " " + words
            if words[-1:].isalnum() and text[end:end + 1].isalnum():
                words += " "
            out.append(text[pos:start])
            out.append(_encode(len(spoken)))
            spoken.append(words)
            pos = end
        if not spoken:
            return text
        out.append(text[pos:])
        return "".join(out)

    def _parse_number(self, raw: str):
        """``"3.000,25"`` -> ``("3000", "25", False)`` using the language's separators."""
        neg = raw[:1] in ("-", "−")
        if neg:
            raw = raw[1:]
        ts, ds = self.lang.thousands_sep, self.lang.decimal_sep
        seps = [ch for ch in raw if ch in ".,"]
        if not seps:
            return raw, None, neg
        last = seps[-1]
        if len(set(seps)) == 2 or seps.count(last) > 1:
            if len(set(seps)) == 2:
                cut = raw.rindex(last)
                if seps.count(last) != 1:
                    return None
                whole, frac = raw[:cut], raw[cut + 1:]
                group = "," if last == "." else "."
            else:
                whole, frac, group = raw, None, last
            if not re.fullmatch(r"\d{1,3}(?:%s\d{3})+" % re.escape(group), whole):
                return None
            return whole.replace(group, ""), frac, neg
        whole, frac = raw.split(last)
        if last == ts and len(frac) == 3 and 1 <= len(whole) <= 3:
            return whole + frac, None, neg
        return whole, frac, neg

    def _rule_words(self, rule: Rule, m: "re.Match[str]") -> Optional[str]:
        parts = rule.spoken.split(NUMBER)
        if len(parts) == 1:
            return rule.spoken
        index = int(m.lastgroup[1:])
        nouns = self.lexicon.unit_nouns
        out = [parts[0]]
        for j, tail in enumerate(parts[1:]):
            raw = m.groupdict().get(f"n{index}_{j}")
            if raw is None:
                out.append(NUMBER + tail)
                continue
            parsed = self._parse_number(raw)
            if parsed is None:
                return None
            ip, frac, neg = parsed
            one = frac is None and not neg and len(ip) <= _MAX_INT_DIGITS and int(ip) == 1
            gender = rule.gender if j == 0 else None
            noun = re.match(r"\s*[^\W\d_][\w-]*", tail)
            if noun is not None:
                word = noun.group().strip()
                if j == 0 and rule.plural is not None:
                    if not one:
                        tail = tail.replace(word, rule.plural, 1)
                elif word in nouns:
                    form = nouns[word]
                    gender = gender or form.gender
                    tail = tail.replace(word, form.pick(one), 1)
            out.append(self._words(ip, frac, neg, None if frac is not None else gender) + tail)
        return "".join(out)

    def _spelled_sub(self, m: "re.Match[str]") -> str:
        parts = re.findall(r"[^\W\d_]|\d+", m.group())
        return " ".join(self.lang.cardinal(int(p)) if p.isdigit() else p for p in parts)

    def _isotope_sub(self, m: "re.Match[str]") -> str:
        el = m.group("el")
        name = self.lexicon.elements.get(el) or " ".join(el)  # "cobalt", else "C o"
        meta = " m" if m.group("meta") else ""
        return f"{name} {self.lang.cardinal(int(m.group('n')))}{meta}"

    @staticmethod
    def _punct_sub(m: "re.Match[str]", c: _Compiled) -> str:
        rep = c.punct[m.group("p")]
        text, start, end = m.string, m.start(), m.end()
        if start == 0 or text[start - 1] == "\n" or end == len(text) or text[end] == "\n":
            return ""  # a dash opening or closing a line has nothing to pause between
        mark = rep.strip()
        if len(mark) == 1 and mark in ",;:":
            if text[end] in ".,;:!?":
                return ""
            if text[start - 1] == mark:
                return " "
        return rep

    def _abbr_sub(self, m: "re.Match[str]", c: _Compiled) -> str:
        entry = c.abbr[re.sub(r"\s+", "", m.group())]
        text, end = m.string, m.end()
        if entry.to and m.group().endswith("."):
            nxt = text[end:end + 3]
            if end == len(text) or nxt[:1] == "\n" or (
                    entry.final and nxt[:1].isspace() and nxt.lstrip()[:1].isupper()):
                return entry.to + "."
        return entry.to

    def _date_sub(self, m: "re.Match[str]") -> str:
        before = m.string[max(0, m.start() - 12):m.start()]
        return self.lang.format_date(m, before) or m.group()

    def _pre_sub(self, m: "re.Match[str]", c: _Compiled) -> str:
        s, g = c.sym, m.group()
        if g[0] == "^":
            exp = m.group("exp")
            if exp == "2" and "^2" in s:
                return " " + s["^2"]
            if exp == "3" and "^3" in s:
                return " " + s["^3"]
            return f" {s['^']} {exp}" if "^" in s else g
        if g.strip() in ("*", "/"):
            return f" {c.ops[g.strip()]} "
        if g == "#":
            return s["#"] + " " if "#" in s else g
        if g == "+":
            return s["+"] + " " if "+" in s else g
        return f" {s['−']} " if "−" in s else g

    def _let_sub(self, m: "re.Match[str]", c: _Compiled) -> str:
        """A letter symbol, spaced only where it touches a letter or digit: "Δt", "α-Teilchen"."""
        text, start, end = m.string, m.start(), m.end()
        before, after = text[start - 1:start], text[end:end + 1]
        # a letter before that is replaced as well already brings its space: "ℏω"
        left = " " if (before.isalpha() and before not in c.sym) or before.isdecimal() else ""
        return f"{left}{c.sym[m.group()]}{' ' if after.isalpha() or after.isdecimal() else ''}"

    def _vulgar_sub(self, m: "re.Match[str]") -> str:
        num, den = _VULGAR[m.group(2)]
        if m.group(1) is None:
            return self.lang.fraction(num, den)
        return self.lang.mixed_fraction(int(m.group(1)), num, den)

    def _post_sub(self, m: "re.Match[str]", c: _Compiled) -> str:
        s = c.sym
        if m.group("sq"):
            return " " + s[m.group("sq")]
        for name in ("mop", "op", "eq", "cmp", "amp"):
            if name in m.re.groupindex and m.group(name):
                word = s.get(m.group(name))
                if not word:
                    return m.group()
                if name == "amp":
                    return word
                if name == "op":  # no space at the text's edges, inside brackets or before punctuation
                    text, start, end = m.string, m.start(), m.end()
                    before, after = text[start - 1:start], text[end:end + 1]
                    left = " " if before and not before.isspace() and before not in "([{" else ""
                    right = " " if after and not after.isspace() and after not in ")]}.,;:!?" else ""
                    return f"{left}{word}{right}"
                return f" {word} "
        return m.group()

    # ------------------------------------------------------------------ numbers
    def _numbers(self, text: str, c: _Compiled) -> str:
        out = []
        pos = 0
        search = c.token_re.search
        while True:
            m = search(text, pos)
            if not m:
                break
            words, end = self._render(m, text, c)
            out.append(text[pos:m.start()])
            out.append(words)
            pos = end
        out.append(text[pos:])
        return "".join(out)

    def _words(self, intpart: str, frac: Optional[str], neg: bool, gender: Optional[str] = None) -> str:
        lang = self.lang
        if (len(intpart) > 1 and intpart[0] == "0") or len(intpart) > _MAX_INT_DIGITS:
            words = lang.digits(intpart)
        else:
            # a gender only shows on exactly 1: "eine Stunde", but "hunderteins Stunden" and
            # "eins Komma fünf Kilogramm"
            value = int(intpart)
            words = lang.cardinal(value, gender if frac is None and value == 1 else None)
        if frac is not None:
            words += f" {lang.point} {lang.digits(frac)}"
        return f"{lang.minus} {words}" if neg else words

    def _render(self, m: "re.Match[str]", text: str, c: _Compiled):
        lang, lex = self.lang, self.lexicon
        neg = m.group("neg") is not None or ("neg0" in m.re.groupindex and m.group("neg0") is not None)
        end = m.end()

        if m.group("frac"):
            a, b = m.group("frac").split("/")
            words = lang.fraction(int(a), int(b))
            return (f"{lang.minus} {words}" if neg else words), end

        if m.group("time"):
            hh, mm = int(m.group("hh")), int(m.group("mm"))
            suffix = None
            sm = c.suffix_re.match(text, end)
            if sm and sm.group("ampm") and 1 <= hh <= 12:
                suffix, end = sm.group("ampm").strip(), sm.end()
            if hh < 24:
                if lang.time_word:  # "14:30 Uhr": the time already says it
                    um = _time_word_re(lang.time_word).match(text, end)
                    end = um.end() if um else end
                return lang.time(hh, mm, suffix), end
            return f"{self.lang.cardinal(hh)} {self.lang.cardinal(mm)}", end

        raw = m.group("num")
        if m.group("ver"):
            return f" {lang.point} ".join(self._words(p, None, False) for p in raw.split(".")), end
        if m.group("th"):
            raw = re.sub(rf"[{re.escape(lang.thousands_sep)} {_NBSP}]", "", raw)
        if lang.decimal_sep != ".":
            raw = raw.replace(lang.decimal_sep, ".")
        intpart, sep, frac = raw.partition(".")
        frac = frac if sep else None
        one = frac is None and int(intpart) == 1 if len(intpart) <= _MAX_INT_DIGITS else False

        # prefix currency: "$5", "€3,50", "$5 million"
        cur_sym = m.group("cur") if "cur" in m.re.groupindex else None
        if cur_sym:
            scale = c.scale_re.match(text, end) if c.scale_re else None
            if scale:
                cur = lex.currencies[cur_sym]
                words = f"{self._words(intpart, frac, neg)} {scale.group('scale')} {cur.major.plural}"
                return words, scale.end()
            return self._currency(cur_sym, intpart, frac, neg), end

        sm = c.suffix_re.match(text, end)
        if sm:
            kind = sm.lastgroup
            if kind == "pct":
                return f"{self._words(intpart, frac, neg)} {lang.percent}", sm.end()
            if kind == "csuf" or kind == "csym":
                return self._currency(sm.group("csym"), intpart, frac, neg), sm.end()
            if kind == "ord" and frac is None and not neg and len(intpart) <= _MAX_INT_DIGITS:
                return lang.ordinal(int(intpart)), sm.end()
            if kind == "dec" and frac is None and not neg and len(intpart) == 4 \
                    and 1000 <= int(intpart) <= 2090 and intpart[-1] == "0":
                return lang.decade(int(intpart)), sm.end()
            if kind == "ampm" and frac is None and 1 <= int(intpart) <= 12 and not neg:
                return lang.time(int(intpart), 0, sm.group("ampm").strip()), sm.end()
            if kind in ("unit", "uf", "ua", "den"):
                sym = sm.group("uf") or sm.group("ua")
                if sym:
                    form = lex.units[sym]
                    words = f"{self._words(intpart, frac, neg, form.gender)} {form.pick(one)}"
                    if sm.group("den"):
                        words += f" {lang.per_word} {lex.units[sm.group('den')].singular}"
                    return words, sm.end()

        # plain number; maybe a year
        if (frac is None and not neg and len(intpart) == 4 and 1100 <= int(intpart) <= 2099
                and c.year_re and c.year_re.search(text[max(0, m.start() - 20):m.start()])):
            words = lang.year(int(intpart))
        else:
            # gender of a known unit noun that follows: "1 Stunde" -> "eine Stunde"
            noun = _NEXT_WORD.match(text, end) if frac is None else None
            form = lex.unit_nouns.get(noun.group(1)) if noun else None
            words = self._words(intpart, frac, neg, form.gender if form else None)
        # "3D" -> "three D", but keep "5s" -> "fives"
        if end < len(text) and text[end].isalpha():
            if not (text[end] == "s" and not text[end + 1:end + 2].isalpha()):
                words += " "
        return words, end

    def _currency(self, symbol: str, intpart: str, frac: Optional[str], neg: bool) -> str:
        cur = self.lexicon.currencies[symbol]
        lang = self.lang
        if len(intpart) > _MAX_INT_DIGITS or (frac is not None and (len(frac) > 2 or not cur.minor)):
            words = f"{self._words(intpart, frac, False)} {cur.major.plural}"
        else:
            minor = int(frac.ljust(2, "0")) if frac else None
            words = lang.currency(int(intpart), minor, cur)
        return f"{lang.minus} {words}" if neg else words
