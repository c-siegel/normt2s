"""Editable dictionaries: abbreviations, units, currencies and math symbols.

Built-in data lives in ``normt2s/data/<lang>.json``. Extend or override it with
``add_*`` calls or by loading your own ``.json`` / ``.toml`` file with the same schema.
"""

from __future__ import annotations

import copy
import functools
import json
import threading
import warnings
from importlib import resources
from pathlib import Path
from typing import Callable, Dict, NamedTuple, Optional, Sequence, Set, Union

from .langs import Language


def _locked(fn):
    @functools.wraps(fn)
    def wrapper(self, *a, **kw):
        with self.lock:
            return fn(self, *a, **kw)

    return wrapper


class Form(NamedTuple):
    singular: str
    plural: str
    gender: Optional[str] = None  # "m" / "f" / "n", only relevant for German

    def pick(self, one: bool) -> str:
        return self.singular if one else self.plural


class Currency(NamedTuple):
    major: Form
    minor: Optional[Form]


class Abbreviation(NamedTuple):
    to: str
    # May the abbreviation end a sentence ("... and so on, etc. Then ...")? If yes, set "final: True."
    final: bool = False


class Lexicon:
    def __init__(self, pluralize: Callable[[str], str] = lambda s: s):
        self._pluralize = pluralize
        self.abbreviations: Dict[str, Abbreviation] = {}
        self.units: Dict[str, Form] = {}
        self.currencies: Dict[str, Currency] = {}
        self.symbols: Dict[str, str] = {}
        # operators read only between operands: "*" and " / "
        self.operators: Dict[str, str] = {}
        # LaTeX commands such as "\\times" -> "times" (also bare characters such as "/")
        self.latex_commands: Dict[str, str] = {}
        # LaTeX function names without backslash: "sin" -> "sine"
        self.latex_functions: Dict[str, str] = {}
        # sentence templates for structured LaTeX, e.g. "{a} over {b}"
        self.phrases: Dict[str, str] = {}
        self._explicit: Set[str] = set()
        # bumped on every change so a Normalizer knows when to recompile its regexes
        self.version = 0
        # guards edits and snapshots, so a Normalizer never compiles a half-edited lexicon
        self.lock = threading.RLock()

    def snapshot(self) -> "Lexicon":
        """A copy whose dictionaries can be iterated while other threads edit the original."""
        with self.lock:
            snap = copy.copy(self)
            for name, val in vars(self).items():
                if isinstance(val, (dict, list, set)):
                    setattr(snap, name, copy.copy(val))
            return snap

    # ---------------------------------------------------------------- loading
    @classmethod
    def builtin(cls, lang: Language) -> "Lexicon":
        lex = cls(lang.pluralize)
        text = (resources.files("normt2s") / "data" / f"{lang.code}.json").read_text("utf-8")
        lex.update(json.loads(text))
        return lex

    def load(self, path: Union[str, Path]) -> "Lexicon":
        """Merge a ``.json`` or ``.toml`` file into this lexicon (entries override built-ins)."""
        path = Path(path)
        if path.suffix == ".toml":
            import tomllib  # Python >= 3.11

            data = tomllib.loads(path.read_text("utf-8"))
        else:
            data = json.loads(path.read_text("utf-8"))
        return self.update(data)

    def update(self, data: dict) -> "Lexicon":
        for key, val in data.get("abbreviations", {}).items():
            if isinstance(val, dict):
                self.add_abbreviation(key, val["to"], final=val.get("final", False))
            else:
                self.add_abbreviation(key, val)
        for sym, val in data.get("units", {}).items():
            self.add_unit(sym, *val)
        for sym, val in data.get("currencies", {}).items():
            self.add_currency(sym, val["major"], val.get("minor"))
        for key, val in data.get("symbols", {}).items():
            self.add_symbol(key, val)
        for key, val in data.get("operators", {}).items():
            self.add_operator(key, val)
        latex = data.get("latex", {})
        for key, val in latex.get("commands", {}).items():
            self.add_latex_command(key, val)
        for key, val in latex.get("functions", {}).items():
            self.add_latex_function(key, val)
        for key, val in latex.get("phrases", {}).items():
            self.add_phrase(key, val)
        return self

    # ------------------------------------------------------------------- edits
    @_locked
    def add_abbreviation(self, key: str, to: str, *, final: bool = False,
                         capitalized: bool = True) -> None:
        """``add_abbreviation("e.g.", "for example")``.

        Matching is case-sensitive. For keys starting with a lowercase letter a capitalized
        variant ("E.g." -> "For example") is derived automatically unless ``capitalized=False``.
        Whitespace inside a key is optional when matching ("z. B." also matches "z.B.").
        """
        self.abbreviations[key] = Abbreviation(to, final)
        self._explicit.add(key)
        if capitalized and key[:1].islower() and to:
            cap = key[0].upper() + key[1:]
            if cap not in self._explicit:
                self.abbreviations[cap] = Abbreviation(to[0].upper() + to[1:], final)
        self.version += 1

    @_locked
    def add_unit(self, symbol: str, singular: str, plural: Optional[str] = None,
                 gender: Optional[str] = None) -> None:
        """``add_unit("kn", "knot")`` -> "5 kn" reads "five knots"."""
        self.units[symbol] = Form(singular, plural or self._pluralize(singular), gender)
        self.version += 1

    @_locked
    def add_currency(self, symbol: str, major: Sequence, minor: Optional[Sequence] = None) -> None:
        """``add_currency("CHF", ("franc", "francs"), ("rappen", "rappen"))``."""
        def form(spec: Sequence) -> Form:
            spec = list(spec) + [None] * (3 - len(spec))
            return Form(spec[0], spec[1] or self._pluralize(spec[0]), spec[2])

        self.currencies[symbol] = Currency(form(major), form(minor) if minor else None)
        self.version += 1

    @_locked
    def add_symbol(self, key: str, word: str) -> None:
        if not key or any(ch.isspace() for ch in key):
            raise ValueError(f"symbol key must be non-empty and contain no whitespace: {key!r}")
        self.symbols[key] = word
        self.version += 1

    @_locked
    def add_operator(self, key: str, word: str) -> None:
        """``add_operator("*", "times")``: read only between operands (``3 * 4``). Keys: ``*``, ``/``."""
        if key not in ("*", "/"):
            raise ValueError("operator key must be '*' or '/'")
        self.operators[key] = word
        self.version += 1

    @_locked
    def add_latex_command(self, name: str, spoken: str) -> None:
        """``add_latex_command("R", "the real numbers")``; the backslash is optional."""
        if name.isalpha():
            name = "\\" + name
        self.latex_commands[name] = spoken
        self.version += 1

    @_locked
    def add_latex_function(self, name: str, spoken: str) -> None:
        """``add_latex_function("sinc", "sinc")`` for ``\\sinc x``.

        For symbol-like commands (``\\cdot``, ``\\times``) use :meth:`add_latex_command` instead:
        commands take precedence over functions with the same name.
        """
        name = name.lstrip("\\")
        command = "\\" + name
        if command in self.latex_commands:
            warnings.warn(
                f"{command} is already a LaTeX command ({self.latex_commands[command]!r}) and "
                f"commands take precedence over functions; use add_latex_command({name!r}, ...) "
                "to change how it is spoken.", UserWarning, stacklevel=2)
        self.latex_functions[name] = spoken
        self.version += 1

    @_locked
    def add_phrase(self, key: str, template: str) -> None:
        """Override a LaTeX sentence template, e.g. ``add_phrase("frac", "{a} divided by {b}")``."""
        self.phrases[key] = template
        self.version += 1

    @_locked
    def remove(self, kind: str, key: str) -> None:
        """``remove("abbreviations", "St.")``; ``kind`` is a Lexicon attribute name."""
        getattr(self, kind).pop(key)
        self.version += 1
