"""User rule sets: literal pronunciation rules that run inside the normalizer pipeline.

A :class:`Rule` is literal text plus one placeholder, ``{number}``. No regular expressions are
accepted from users; the pattern is built (and escaped) here. A :class:`RuleSet` is immutable
and hashable by content, so applications can cache one per user.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

NUMBER = "{number}"
MAX_TERM = 200
MAX_RULES = 2000

# both languages' formats: 5, 1,5, 3.000,25, 1,234.5 (parsed per language by the Normalizer)
_NUM_RE = r"(?:[-−](?=\d))?\d+(?:[.,]\d+)*"
_GUARD_L = {"letter": r"(?<![^\W\d_])", "digit": r"(?<![^\W_])"}
_GUARD_R = {"letter": r"(?![^\W\d_])", "digit": r"(?![^\W_])"}

_CAMEL = {"caseSensitive": "case_sensitive", "wholeWord": "whole_word"}


@dataclass(frozen=True)
class Rule:
    """``Rule("pH", "p H")`` or ``Rule("{number} kg", "{number} kilograms")``.

    ``gender`` and ``plural`` refine the first ``{number}`` of ``spoken``: the number is read in
    that gender, and ``plural`` replaces the word after it when the value is not exactly 1.
    """

    term: str
    spoken: str
    whole_word: bool = True
    case_sensitive: bool = False
    gender: Optional[str] = None
    plural: Optional[str] = None


def _edge(term: str, last: bool) -> Optional[str]:
    if term.endswith(NUMBER) if last else term.startswith(NUMBER):
        return "digit"
    ch = term[-1] if last else term[0]
    if ch.isalpha():
        return "letter"
    if ch.isdigit():
        return "digit"
    return None


def _first_chars(rule: Rule) -> Optional[set]:
    """Characters a match can start with (``None``: starts with whitespace, any position)."""
    term = rule.term
    if term.startswith(NUMBER):
        return set("0123456789-−")
    ch = term[0]
    if ch.isspace():
        return None
    chars = {ch}
    if not rule.case_sensitive:
        chars |= {ch.lower(), ch.upper(), ch.title(), ch.casefold()[:1]}
    return chars


def _body(index: int, rule: Rule, term: Optional[str] = None) -> str:
    """Pattern of ``rule`` (or, with ``term``, of a prefix of its term, as an unnamed group)."""
    partial = term is not None
    term = rule.term if term is None else term
    pieces = []
    for j, part in enumerate(term.split(NUMBER)):
        if j:
            pieces.append(f"(?:{_NUM_RE})" if partial else f"(?P<n{index}_{j - 1}>{_NUM_RE})")
        if part:
            pieces.append(r"\s+".join(re.escape(w) for w in re.split(r"\s+", part)))
    body = "".join(pieces)
    if not rule.case_sensitive:
        body = f"(?i:{body})"
    if rule.whole_word:
        left, right = _edge(term, False), _edge(term, True)
        body = _GUARD_L.get(left, "") + body + ("" if partial else _GUARD_R.get(right, ""))
    return body if partial else f"(?P<r{index}>{body})"


class RuleSet:
    """An immutable collection of :class:`Rule` objects.

    >>> RuleSet([Rule("pH", "p H", case_sensitive=True)])
    RuleSet(1 rule)
    """

    __slots__ = ("_rules", "_scan_data", "_partial", "_lock")

    def __init__(self, rules: Iterable[Rule] = ()):
        items: List[Rule] = []
        for r in rules:
            if not isinstance(r, Rule):
                raise TypeError(f"RuleSet expects Rule objects, got {type(r).__name__}")
            if not r.term:
                continue
            if len(r.term) > MAX_TERM:
                raise ValueError(f"rule term longer than {MAX_TERM} characters: {r.term[:30]!r}...")
            items.append(r)
        if len(items) > MAX_RULES:
            raise ValueError(f"more than {MAX_RULES} rules")
        object.__setattr__(self, "_rules", tuple(items))
        object.__setattr__(self, "_scan_data", None)
        object.__setattr__(self, "_partial", False)
        object.__setattr__(self, "_lock", threading.Lock())

    def __setattr__(self, name, value):
        raise AttributeError("RuleSet is immutable")

    # ---------------------------------------------------------------- constructors
    @classmethod
    def from_dicts(cls, dicts: Iterable[Dict[str, Any]]) -> "RuleSet":
        """Build from dictionaries (``term``, ``spoken``, optional flags; camelCase accepted)."""
        rules = []
        for d in dicts:
            if not isinstance(d, dict):
                raise ValueError(f"rule must be an object, got {type(d).__name__}")
            d = {_CAMEL.get(k, k): v for k, v in d.items()}
            unknown = set(d) - {"term", "spoken", "whole_word", "case_sensitive", "gender", "plural"}
            if unknown:
                raise ValueError(f"unknown rule keys: {sorted(unknown)}")
            if not isinstance(d.get("term"), str) or not isinstance(d.get("spoken"), str):
                raise ValueError("a rule needs string 'term' and 'spoken'")
            for flag in ("whole_word", "case_sensitive"):
                if flag in d and not isinstance(d[flag], bool):
                    raise ValueError(f"'{flag}' must be true or false")
            rules.append(Rule(**d))
        return cls(rules)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "RuleSet":
        """Load ``{"rules": [ ... ]}`` (or a plain list) from a JSON file."""
        data = json.loads(Path(path).read_text("utf-8"))
        if isinstance(data, dict):
            data = data.get("rules", [])
        return cls.from_dicts(data)

    # ----------------------------------------------------------- value semantics
    @property
    def rules(self) -> Tuple[Rule, ...]:
        return self._rules

    def __iter__(self) -> Iterator[Rule]:
        return iter(self._rules)

    def __len__(self) -> int:
        return len(self._rules)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RuleSet) and self._rules == other._rules

    def __hash__(self) -> int:
        return hash(self._rules)

    def __repr__(self) -> str:
        n = len(self._rules)
        return f"RuleSet({n} rule{'s' if n != 1 else ''})"

    # ---------------------------------------------------------------- matching
    def _data(self):
        data = self._scan_data
        if data is None:
            with self._lock:
                data = self._scan_data
                if data is None:
                    data = _build(self._rules)
                    object.__setattr__(self, "_scan_data", data)
        return data

    def dangling(self, text: str) -> bool:
        """Does ``text`` end inside what could still become a multi-word rule match?

        A stream must not cut there: ``"... e. "`` for the rule ``e. g.``.
        """
        pat = self._partial
        if pat is False:
            with self._lock:
                pat = self._partial
                if pat is False:
                    bodies = []
                    for rule in self._rules:
                        words = re.split(r"(\s+)", rule.term)
                        for k in range(1, len(words), 2):
                            prefix = "".join(words[:k]).rstrip()
                            if prefix and prefix != rule.term:
                                bodies.append(_body(0, rule, prefix))
                    pat = re.compile("(?:" + "|".join(bodies) + r")\s*\Z") if bodies else None
                    object.__setattr__(self, "_partial", pat)
        return pat is not None and pat.search(text, max(0, len(text) - MAX_TERM - 8)) is not None

    def scan(self, text: str) -> Iterator[Tuple["re.Match[str]", Rule]]:
        """Left-to-right, non-overlapping matches with the rule that produced each."""
        data = self._data()
        if data is None:
            return
        cand, words, lens, other, rank, rules = data
        pos, n = 0, len(text)
        while pos < n:
            f = cand.search(text, pos)
            if not f:
                return
            p = f.start()
            best, best_rank = None, 1 << 30
            ch = text[p]
            if ch.isalpha():
                for ln in lens:
                    bucket = words[ln].get(text[p:p + ln].lower())
                    if bucket is not None:
                        m = bucket.match(text, p)
                        if m is not None and rank[int(m.lastgroup[1:])] < best_rank:
                            best, best_rank = m, rank[int(m.lastgroup[1:])]
            bucket = other.get(ch)
            if bucket is not None:
                m = bucket.match(text, p)
                if m is not None and rank[int(m.lastgroup[1:])] < best_rank:
                    best, best_rank = m, rank[int(m.lastgroup[1:])]
            if best is not None and best.end() > p:
                yield best, rules[int(best.lastgroup[1:])]
                pos = best.end()
            else:
                pos = p + 1


def _lead(rule: Rule) -> Optional[str]:
    """Lower-cased first (up to 3) literal characters of a rule that can only start a word."""
    term = rule.term
    if not (rule.whole_word and term[0].isalpha()):
        return None
    lead = term.split(NUMBER)[0].split()[0] if term.split() else ""
    return lead[:3].lower() if lead and lead[0].isalpha() else None


def _build(rules: Tuple[Rule, ...]):
    if not rules:
        return None
    order = sorted(range(len(rules)), key=lambda i: (
        -len(rules[i].term.replace(NUMBER, "")), NUMBER in rules[i].term,
        not rules[i].case_sensitive, i))
    rank = {i: r for r, i in enumerate(order)}
    word_groups: Dict[int, Dict[str, List[int]]] = {}
    other_groups: Dict[str, List[int]] = {}
    wild: List[int] = []
    for i in order:
        key = _lead(rules[i])
        if key is not None:
            word_groups.setdefault(len(key), {}).setdefault(key, []).append(i)
            continue
        chars = _first_chars(rules[i])
        if chars is None:
            wild.append(i)
        else:
            for ch in chars:
                other_groups.setdefault(ch, []).append(i)
    if wild:  # a term starting with a blank can match anywhere: join every bucket
        for ch in other_groups:
            other_groups[ch] = sorted(set(other_groups[ch]) | set(wild), key=rank.__getitem__)
        other_groups.setdefault(" ", [])
        other_groups[" "] = sorted(set(other_groups[" "]) | set(wild), key=rank.__getitem__)
    compile_ = lambda idx: re.compile("|".join(_body(i, rules[i]) for i in idx))  # noqa: E731
    words = {ln: {k: compile_(v) for k, v in d.items()} for ln, d in word_groups.items()}
    other = {ch: compile_(v) for ch, v in other_groups.items() if v}
    lens = sorted(words, reverse=True)
    parts = []
    if words:
        parts.append(r"(?<![^\W\d_])[^\W\d_]")
    if other:
        parts.append("[" + "".join(re.escape(ch) for ch in other) + "]")
    cand = re.compile("|".join(parts))
    return cand, words, lens, other, rank, rules
