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

from .normalizer import SPAN_RE

_FENCE_RE = re.compile(r"(?s)```.*?```")
_SENTENCE_RE = re.compile(r"[.!?…]+[\"')\]”’»]*[ \t]+")
_INITIAL_RE = re.compile(r"[A-Z]\.|\d{1,2}\.")  # initials and ordinal dots ("3. Mai")


class StreamNormalizer:
    def __init__(self, normalizer, max_buffer: int = 400):
        self._n = normalizer
        self._max = max_buffer
        self._buf = ""

    def feed(self, chunk: str) -> str:
        """Add a chunk; returns the normalized text that is now safe to speak (maybe empty)."""
        self._buf += chunk
        cut = self._find_cut()
        if not cut:
            return ""
        head, self._buf = self._buf[:cut], self._buf[cut:]
        return self._n.normalize(head)

    def flush(self) -> str:
        """Normalize and return whatever is left. Call once the stream has ended."""
        head, self._buf = self._buf, ""
        return self._n.normalize(head)

    # ------------------------------------------------------------------ internals
    def _find_cut(self) -> int:
        buf = self._buf
        n = self._n
        n.ensure_compiled()

        limit = self._open_span_start(buf)
        head = buf[:limit]

        # candidate cut points: after a newline, or after sentence punctuation + whitespace
        cuts = [i + 1 for i, c in enumerate(head) if c == "\n"]
        for m in _SENTENCE_RE.finditer(head):
            tok = head[:m.start() + len(m.group().rstrip())].rsplit(None, 1)[-1]
            if tok not in n.no_boundary_tokens and not _INITIAL_RE.fullmatch(tok):
                cuts.append(m.end())
        if cuts:
            # a cut must not fall inside a code / URL / math span
            spans = [m.span() for m in SPAN_RE.finditer(head)]
            for cut in sorted(cuts, reverse=True):
                if not any(a < cut < b for a, b in spans):
                    return cut

        if len(head) > self._max:
            for m in reversed(list(re.finditer(r"\s", head))):
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
