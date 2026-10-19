"""Markdown -> plain text for speech (``Normalizer(markdown="strip")``).

Regex-only and linear: spans that must not be touched (code, URLs, e-mail, HTML, math) are
replaced by private-use placeholders first, then block and inline markers are removed, then the
placeholders are restored. Code content is left as a placeholder so the rest of the pipeline
keeps it verbatim; :func:`restore` puts it back at the very end.
"""

from __future__ import annotations

import re
from typing import List, Tuple

PLACEHOLDER = r"\d+"
_PH_RE = re.compile("(\\d+)")
_FENCE_RE = re.compile(r"```[^\n`]*\n?(.*?)\n?```", re.S)

_MAX = 500  # longest emphasised run; keeps unclosed markers from scanning the whole input

_HR = re.compile(r"^[ \t]*([-*_])[ \t]*(?:\1[ \t]*){2,}$", re.M)
_BLOCK = re.compile(r"^(?:[ \t]{0,3}#{1,6}[ \t]+|(?:[ \t]*>)+[ \t]*|[ \t]*[-*+][ \t]+|[ \t]*\d+[.)][ \t]+)",
                    re.M)
_LINK = re.compile("(!?)\\[([^\\]\\n]*)(\\d+)")
_BOLD = re.compile(r"\*\*(?=\S)(.{1,%d}?)(?<=\S)\*\*|(?<!\w)__(?=\S)(.{1,%d}?)(?<=\S)__(?!\w)"
                   % (_MAX, _MAX))
_ITALIC = re.compile(
    r"(?<![\d)\]*\\])\*(?![\s*])(.{1,%d}?)(?<![\s*])\*(?![\d(\[*])"
    r"|(?<!\w)_(?![\s_])(.{1,%d}?)(?<![\s_])_(?!\w)" % (_MAX, _MAX))
_STRIKE = re.compile(r"~~(?=\S)(.{1,%d}?)(?<=\S)~~" % _MAX)
_LETTER = re.compile(r"[^\W\d_]")


def strip(text: str, span_re: "re.Pattern[str]", mid_line: bool = False) -> Tuple[str, List[str]]:
    """Return ``(plain, verbatim)``: text without Markdown markers, and the code contents that
    are still hidden behind placeholders (give them to :func:`restore`)."""
    saved: List[Tuple[str, str]] = []  # (kind, original text); kind: "code" | "link" | "span"

    def mask(m: "re.Match[str]") -> str:
        g = m.group()
        if g.startswith("```"):
            fm = _FENCE_RE.fullmatch(g)
            saved.append(("code", fm.group(1) if fm else g))
        elif g[0] == "`":
            saved.append(("code", g[1:-1]))
        elif g.startswith("]("):
            saved.append(("link", g))
        else:
            saved.append(("span", g))
        return f"{len(saved) - 1}"

    text = span_re.sub(mask, text)

    first = ""
    if mid_line:  # the first line continues text already released: no block markers there
        first, nl, text = text.partition("\n")
        first += nl
    text = _HR.sub("", text)
    text = _BLOCK.sub("", text)
    text = first + text

    def link(m: "re.Match[str]") -> str:
        kind, _ = saved[int(m.group(3))]
        return m.group(2) if kind == "link" else m.group()

    text = _LINK.sub(link, text)
    text = _BOLD.sub(lambda m: m.group(1) or m.group(2), text)

    def italic(m: "re.Match[str]") -> str:
        inner = m.group(1) or m.group(2)
        return inner if _LETTER.search(inner) else m.group()

    text = _ITALIC.sub(italic, text)
    text = _STRIKE.sub(lambda m: m.group(1), text)

    def unmask(m: "re.Match[str]") -> str:
        kind, original = saved[int(m.group(1))]
        return m.group() if kind == "code" else original

    text = _PH_RE.sub(unmask, text)
    return text, [orig for kind, orig in saved]


_LINK_RAW = re.compile(r"!?\[[^\]\n]*\]\([^)\s]*\)")


def inline_spans(text: str, span_re: "re.Pattern[str]") -> List[Tuple[int, int]]:
    """Spans of complete emphasis, strike-through and links; a stream must not cut inside them."""
    masked = span_re.sub(lambda m: "" * len(m.group()), text)
    spans = [m.span() for pat in (_BOLD, _ITALIC, _STRIKE, _LINK_RAW) for m in pat.finditer(masked)]
    return spans


def restore(text: str, verbatim: List[str]) -> str:
    """Put the hidden code contents back."""
    if not verbatim:
        return text
    return _PH_RE.sub(lambda m: verbatim[int(m.group(1))], text)
