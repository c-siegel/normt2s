"""Markdown -> plain text for speech (``Normalizer(markdown="strip")``).

Regex-only and linear: spans that must not be touched (code, URLs, e-mail, HTML, math) are
replaced by private-use placeholders first, then block and inline markers are removed, then the
placeholders are restored. Code content is left as a placeholder so the rest of the pipeline
keeps it verbatim; :func:`restore` puts it back at the very end.
"""

from __future__ import annotations

import re
from typing import List, Tuple

PLACEHOLDER = r"\uE000\d+\uE001"
_PH_RE = re.compile("\uE000(\\d+)\uE001")
_FENCE_RE = re.compile(r"```[^\n`]*\n?(.*?)\n?```", re.S)

_MAX = 500  # longest emphasised run; keeps unclosed markers from scanning the whole input

_HR = re.compile(r"^[ \t]*([-*_])[ \t]*(?:\1[ \t]*){2,}$", re.M)
_BLOCK = re.compile(r"^(?:[ \t]{0,3}#{1,6}[ \t]+|(?:[ \t]*>)+[ \t]*|[ \t]*[-*+][ \t]+|[ \t]*\d+[.)][ \t]+)",
                    re.M)
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
        return f"\uE000{len(saved) - 1}\uE001"

    text = span_re.sub(mask, text)

    first = ""
    if mid_line:  # the first line continues text already released: no block markers there
        first, nl, text = text.partition("\n")
        first += nl
    text = _HR.sub("", text)
    text = _BLOCK.sub("", text)
    text = first + text

    text = _links(text, saved)
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


_LINK_TARGET = re.compile(r"\]\([^)\s]*\)")


def _label_start(text: str, floor: int, end: int) -> int:
    """Index of the ``[`` (or ``![``) opening a link label that ends at ``end``, else -1."""
    j = text.rfind("[", floor, end)
    if j < 0 or "]" in text[j + 1:end] or "\n" in text[j + 1:end]:
        return -1
    return j - 1 if j > floor and text[j - 1] == "!" else j


def _links(text: str, saved: List[Tuple[str, str]]) -> str:
    """``[label]<link target>`` -> ``label`` (the target is a placeholder). Linear time."""
    out, pos, floor = [], 0, 0
    for m in _PH_RE.finditer(text):
        if saved[int(m.group(1))][0] != "link":
            continue
        start = _label_start(text, max(pos, floor), m.start())
        floor = m.end()
        if start < 0:
            continue
        label_from = text.index("[", start) + 1
        out.append(text[pos:start])
        out.append(text[label_from:m.start()])
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def inline_spans(text: str, span_re: "re.Pattern[str]") -> List[Tuple[int, int]]:
    """Spans of complete emphasis, strike-through and links; a stream must not cut inside them."""
    masked = span_re.sub(lambda m: "\uE001" * len(m.group()), text)
    spans = [m.span() for pat in (_BOLD, _ITALIC, _STRIKE) for m in pat.finditer(masked)]
    floor = 0
    for m in _LINK_TARGET.finditer(text):
        start = _label_start(text, floor, m.start())
        floor = m.end()
        if start >= 0:
            spans.append((start, m.end()))
    return spans


def restore(text: str, verbatim: List[str]) -> str:
    """Put the hidden code contents back."""
    if not verbatim:
        return text
    return _PH_RE.sub(lambda m: verbatim[int(m.group(1))], text)
