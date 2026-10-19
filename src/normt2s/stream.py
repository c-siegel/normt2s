"""Chunk-safe wrapper for streaming LLM output.

``feed()`` buffers text and only releases (normalized) text up to a boundary where no number,
unit, abbreviation, code span or math span can still be completed by later tokens:

* a newline, or sentence punctuation followed by whitespace (not after an abbreviation),
* never inside an open code fence, inline code or LaTeX span,
* as a fallback for very long runs without a boundary: a whitespace that does not follow a
  number or currency symbol.
"""

from __future__ import annotations

import re

from . import markdown as _md
from .normalizer import SPAN_RE

_FENCE_RE = re.compile(r"(?s)```.*?```")
_SENTENCE_RE = re.compile(r"(?<![.!?…])[.!?…]+[\"')\]”’»]*[ \t]+")
_CODE_RE = re.compile(r"`[^`\n]*`")
_OPEN_STAR = re.compile(r"(?<![\d)\]*\\])\*(?![\s*])")
_OPEN_UNDER = re.compile(r"(?<!\w)_(?![\s_])")
_CLOSE_STAR = re.compile(r"(?<![\s*])\*(?![\d(\[*])")
_CLOSE_UNDER = re.compile(r"(?<![\s_])_(?!\w)")
_INITIAL_RE = re.compile(r"[A-Z]\.|\d{1,2}\.")  # initials and ordinal dots ("3. Mai")


class StreamNormalizer:
    def __init__(self, normalizer, max_buffer: int = 400, rules=None):
        self._n = normalizer
        self._max = max_buffer
        self._rules = rules
        self._buf = ""
        self._mid_line = False  # does the next text continue a line already released?

    def _release(self, head: str) -> str:
        out = self._n.normalize(head, self._rules, _mid_line=self._mid_line)
        if head:
            self._mid_line = not head.endswith("\n")
        return out

    def feed(self, chunk: str) -> str:
        """Add a chunk; returns the normalized text that is now safe to speak (maybe empty)."""
        self._buf += chunk
        cut = self._find_cut()
        if not cut:
            return ""
        head, self._buf = self._buf[:cut], self._buf[cut:]
        return self._release(head)

    def flush(self) -> str:
        """Normalize and return whatever is left. Call once the stream has ended."""
        head, self._buf = self._buf, ""
        return self._release(head)

    # ------------------------------------------------------------------ internals
    def _find_cut(self) -> int:
        buf = self._buf
        n = self._n
        n.ensure_compiled()

        limit = self._open_span_start(buf)
        if n._markdown:
            limit = _open_markdown_start(buf, limit)
        head = buf[:limit]

        # candidate cut points: after a newline, or after sentence punctuation + whitespace
        cuts = [i + 1 for i, c in enumerate(head) if c == "\n"]
        for m in _SENTENCE_RE.finditer(head):
            tok = head[:m.start() + len(m.group().rstrip())].rsplit(None, 1)[-1]
            if tok not in n.no_boundary_tokens and not _INITIAL_RE.fullmatch(tok):
                cuts.append(m.end())
        # a cut must not fall inside a code / URL / math span (or, for Markdown, a complete
        # emphasis or link)
        spans = [m.span() for m in SPAN_RE.finditer(head)]
        if n._markdown:
            spans += _md.inline_spans(head, SPAN_RE)
        if self._rules is not None:  # a rule such as "e. g." may contain a sentence mark
            spans += [m.span() for m, _ in self._rules.scan(head)]
        if cuts:
            for cut in sorted(cuts, reverse=True):
                if not any(a < cut < b for a, b in spans) and not (
                        self._rules is not None and self._rules.dangling(head[:cut])):
                    return cut

        if len(head) > self._max:
            for m in reversed(list(re.finditer(r"\s", head))):
                if n._markdown and any(a < m.end() < b for a, b in spans):
                    continue
                prev = head[:m.start()].rsplit(None, 1)
                prev = prev[-1] if prev else ""
                if not prev or prev[-1].isdigit() or prev in n.no_boundary_tokens \
                        or prev[-1] in "$€£¥-−":
                    continue
                return m.end()
        return 0

    @staticmethod
    def _open_span_start(buf: str) -> int:
        """Index where an unterminated code/math span begins, else ``len(buf)``."""
        limit = len(buf)
        if buf.count("```") % 2:
            limit = buf.rfind("```")
        head = _FENCE_RE.sub(lambda m: " " * len(m.group()), buf[:limit])
        if head.count("`") % 2:
            limit = head.rfind("`")
        head = buf[:limit]
        for open_, close in (("\\(", "\\)"), ("\\[", "\\]")):
            if head.count(open_) > head.count(close):
                limit = min(limit, head.rfind(open_))
        if head.count("$$") % 2:
            limit = min(limit, head.rfind("$$"))
        # a lone "$" may open inline math; hold back only if one is open on the current line
        line_start = head.rfind("\n") + 1
        tail = head[line_start:limit] if limit >= line_start else ""
        if tail.count("$") % 2 and "$$" not in tail:
            limit = min(limit, line_start + tail.rfind("$"))
        return limit


def _open_markdown_start(buf: str, limit: int) -> int:
    """Hold back an unclosed ``**``, ``__``, ``~~``, ``*x``, ``_x`` or ``[text](`` on the current line."""
    line_start = buf.rfind("\n", 0, limit) + 1
    tail = _CODE_RE.sub(lambda m: " " * len(m.group()), buf[line_start:limit])
    cut = len(tail)
    for mark in ("**", "__", "~~"):
        if tail.count(mark) % 2:
            cut = min(cut, tail.rfind(mark))
    for opener, closer in ((_OPEN_STAR, _CLOSE_STAR), (_OPEN_UNDER, _CLOSE_UNDER)):
        last = None
        for last in opener.finditer(tail):
            pass
        if last is not None and not closer.search(tail, last.end()):
            cut = min(cut, last.start())
    lb = tail.rfind("[")
    if lb >= 0:
        rb = tail.find("]", lb)
        if rb < 0 or rb == len(tail) - 1 or (tail[rb + 1] == "(" and ")" not in tail[rb:]):
            cut = min(cut, lb - 1 if lb and tail[lb - 1] == "!" else lb)
    return min(limit, line_start + cut)
