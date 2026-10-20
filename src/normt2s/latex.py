"""LaTeX -> spoken words.

A small tokenizer + recursive-descent parser builds a tree of tuples, a renderer walks it and
speaks it. All vocabulary (symbols, function names, sentence templates) comes from the
:class:`~normt2s.lexicon.Lexicon`, so it is translatable and user-extensible.

Malformed input never raises out of :meth:`LatexSpeaker.speak`; it returns ``None`` and the
caller keeps the original LaTeX.
"""

from __future__ import annotations

import re
from typing import List, Optional

_TOKEN_PATTERN = r"""(?P<cmd>\\(?:[A-Za-z]+\*?|[^A-Za-z]))
      | (?P<num>{comma}\d+(?:\.\d+)?(?:\{{,\}}\d+)?)
      | (?P<let>[A-Za-z])
      | (?P<ws>\s+)
      | (?P<sym>.)"""
_TOKEN_RE = re.compile(_TOKEN_PATTERN.format(comma=""), re.X | re.S)
# Languages with a decimal comma also read a bare "1,23" as a number. Lists ("1, 2"), chains
# ("1,2,3") and the digit after one ("2" in "1,2,3") stay separate tokens.
_TOKEN_RE_COMMA = re.compile(_TOKEN_PATTERN.format(comma=r"(?<!\d,)\d+,\d+(?!,?\d)|"),
                             re.X | re.S)

_IGNORE = {",", ";", ":", "!", " ", "quad", "qquad", "displaystyle", "textstyle", "scriptstyle",
           "scriptscriptstyle", "limits", "nolimits", "big", "Big", "bigg", "Bigg", "bigl", "bigr",
           "Bigl", "Bigr", "biggl", "biggr", "nonumber", "notag", "hline", "centering", "middle",
           "relax", "protect"}
_DROP_ARG = {"label", "tag", "hspace", "vspace", "phantom", "hphantom", "vphantom"}
_ACCENTS = {"vec": "vec", "hat": "hat", "widehat": "hat", "bar": "bar", "overline": "bar",
            "dot": "dot", "ddot": "ddot", "tilde": "tilde", "widetilde": "tilde",
            "overrightarrow": "vec", "pmod": "pmod"}
_TEXTLIKE = {"text", "textrm", "textbf", "textit", "textsf", "texttt", "mbox", "mathrm",
             "mathsf", "mathtt", "operatorname"}
_STYLE = {"mathbf", "mathit", "boldsymbol", "bm", "mathcal", "mathscr", "mathfrak", "boxed",
          "underline", "mathnormal", "pmb", "cancel"}
_OPENERS = {"lfloor": ("\\rfloor", "floor"), "lceil": ("\\rceil", "ceil"),
            "langle": ("\\rangle", "angle")}
_BIGOPS = {"sum": "sum", "prod": "prod", "int": "int", "iint": "iint", "iiint": "iiint",
           "oint": "oint", "lim": "lim", "limsup": "lim", "liminf": "lim", "bigcup": "bigcup",
           "bigcap": "bigcap"}
_MATRIX_ENVS = {"matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix", "Vmatrix", "smallmatrix",
                "array"}
_FUNC_LETTERS = set("fghFGHP")
_OPERATOR_CMDS = {"times", "cdot", "div", "pm", "mp", "neq", "ne", "leq", "le", "geq", "ge",
                  "approx", "sim", "equiv", "propto", "to", "rightarrow", "Rightarrow",
                  "Leftrightarrow", "iff", "in", "notin", "subset", "subseteq", "supset", "cup",
                  "cap", "setminus", "mid", "land", "lor", "wedge", "vee", "ldots", "cdots", "dots",
                  "mapsto", "ll", "gg", "cong", "perp", "parallel", "ast", "oplus", "otimes",
                  "circ", "implies", "leftrightarrow", "Leftarrow", "leftarrow"}
_PAREN_STOP = {")", "]", "}", "\\right", "\\end", "\\}", "\\rfloor", "\\rceil", "\\rangle"}
_OPEN_PHRASE = {"(": "open_paren", "[": "open_bracket", "⟨": "open_angle"}
_CLOSE_PHRASE = {")": "close_paren", "]": "close_bracket", "⟩": "close_angle"}

GREEK = {
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "delta": "delta", "epsilon": "epsilon",
    "varepsilon": "epsilon", "zeta": "zeta", "eta": "eta", "theta": "theta", "vartheta": "theta",
    "iota": "iota", "kappa": "kappa", "lambda": "lambda", "mu": "mu", "nu": "nu", "xi": "xi",
    "pi": "pi", "varpi": "pi", "rho": "rho", "varrho": "rho", "sigma": "sigma",
    "varsigma": "sigma", "tau": "tau", "upsilon": "upsilon", "phi": "phi", "varphi": "phi",
    "chi": "chi", "psi": "psi", "omega": "omega", "Gamma": "capital gamma",
    "Delta": "capital delta", "Theta": "capital theta", "Lambda": "capital lambda",
    "Xi": "capital xi", "Pi": "capital pi", "Sigma": "capital sigma",
    "Upsilon": "capital upsilon", "Phi": "capital phi", "Psi": "capital psi",
    "Omega": "capital omega",
}


def _decimal(text: str) -> str:
    """Normalize a number token's decimal mark ("{,}" or a bare ",") to "."."""
    return text.replace("{,}", ".").replace(",", ".")


class _Tok:
    __slots__ = ("kind", "text", "start", "end")

    def __init__(self, kind, text, start, end):
        self.kind, self.text, self.start, self.end = kind, text, start, end


def _tokenize(src: str, decimal_comma: bool = False) -> List[_Tok]:
    toks = []
    for m in (_TOKEN_RE_COMMA if decimal_comma else _TOKEN_RE).finditer(src):
        kind, text = m.lastgroup, m.group()
        if kind == "ws":
            continue
        if kind == "cmd":
            if text in ("\\|", "\\Vert", "\\lVert", "\\rVert"):
                kind, text = "sym", "‖"
            elif text in ("\\vert", "\\lvert", "\\rvert"):
                kind, text = "sym", "|"
        toks.append(_Tok(kind, text, m.start(), m.end()))
    return toks


class _Parser:
    def __init__(self, src: str, toks: List[_Tok]):
        self.src, self.toks, self.i = src, toks, 0

    # --- helpers
    def peek(self) -> Optional[_Tok]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _is_sym(self, tok, text) -> bool:
        return tok is not None and tok.kind == "sym" and tok.text == text

    def parse_seq(self, closers=frozenset(), set_mode=False) -> list:
        nodes = []
        while True:
            t = self.peek()
            if t is None or t.text in closers:
                break
            nodes.append(self.parse_scripts(self.parse_atom()))
        return self._fix_bars(nodes, set_mode)

    def parse_arg(self, single=True) -> list:
        t = self.peek()
        if t is None:
            return []
        if self._is_sym(t, "{"):
            self.i += 1
            inner = self.parse_seq({"}"})
            if self._is_sym(self.peek(), "}"):
                self.i += 1
            return inner
        if t.kind == "num" and single and len(t.text) > 1 and t.text.isdigit():
            # \frac12 means \frac{1}{2}
            rest = _Tok("num", t.text[1:], t.start + 1, t.end)
            self.toks[self.i] = _Tok("num", t.text[0], t.start, t.start + 1)
            self.toks.insert(self.i + 1, rest)
        if t.kind == "sym" and t.text in "([":
            self.i += 1
            return [("sym", t.text)]
        return [self.parse_atom()]

    def parse_raw_arg(self) -> str:
        t = self.peek()
        if not self._is_sym(t, "{"):
            if t is None:
                return ""
            self.i += 1
            return t.text
        depth, j = 1, self.i + 1
        while j < len(self.toks):
            tj = self.toks[j]
            if tj.kind == "sym" and tj.text == "{":
                depth += 1
            elif tj.kind == "sym" and tj.text == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        end = self.toks[j].start if j < len(self.toks) else len(self.src)
        raw = self.src[t.end:end]
        self.i = j + 1
        return raw

    def parse_scripts(self, node):
        sub = sup = None
        primes = 0
        while True:
            t = self.peek()
            if self._is_sym(t, "^"):
                self.i += 1
                sup = self.parse_arg()
            elif self._is_sym(t, "_"):
                self.i += 1
                sub = self.parse_arg()
            elif self._is_sym(t, "'") or (t is not None and t.text == "\\prime"):
                self.i += 1
                primes += 1
            else:
                break
        if sub is None and sup is None and not primes:
            return node
        return ("script", node, sub, sup, primes)

    # --- atoms
    def parse_atom(self):
        t = self.toks[self.i]
        self.i += 1
        k, x = t.kind, t.text
        if k == "num":
            return ("num", x)
        if k == "let":
            return ("let", x)
        if k == "sym":
            if x == "{":
                inner = self.parse_seq({"}"})
                if self._is_sym(self.peek(), "}"):
                    self.i += 1
                return ("group", inner)
            if x in "([":
                return self.parse_paren(x)
            if x == "}":
                return ("drop",)
            return ("sym", x)
        return self.parse_cmd(x[1:])

    def parse_paren(self, open_):
        save = self.i
        inner = self.parse_seq(_PAREN_STOP)
        t = self.peek()
        if t is not None and t.kind == "sym" and t.text in (")", "]"):
            self.i += 1
            return ("paren", open_, t.text, inner)
        self.i = save
        return ("sym", open_)

    def parse_cmd(self, name: str):
        if name in _IGNORE:
            return ("drop",)
        if name in ("frac", "dfrac", "tfrac", "cfrac"):
            return ("frac", self.parse_arg(), self.parse_arg())
        if name in ("binom", "dbinom", "tbinom"):
            return ("binom", self.parse_arg(), self.parse_arg())
        if name == "sqrt":
            index = None
            if self._is_sym(self.peek(), "["):
                self.i += 1
                index = self.parse_seq({"]"})
                if self._is_sym(self.peek(), "]"):
                    self.i += 1
            return ("sqrt", index, self.parse_arg())
        if name in _ACCENTS:
            return ("acc", _ACCENTS[name], self.parse_arg())
        if name in _TEXTLIKE:
            return ("text", self.parse_raw_arg())
        if name == "mathbb":
            return ("bb", self.parse_raw_arg().strip())
        if name in _STYLE:
            return ("group", self.parse_arg())
        if name in _DROP_ARG:
            self.parse_raw_arg()
            return ("drop",)
        if name == "\\":
            return ("sym", ",")
        if name == "begin":
            return self.parse_env()
        if name == "left":
            return self.parse_left()
        if name in _OPENERS:
            closer, kind = _OPENERS[name]
            inner = self.parse_seq({closer})
            if self.peek() is not None and self.peek().text == closer:
                self.i += 1
                return ("paren", "⟨", "⟩", inner) if kind == "angle" else ("acc", kind, inner)
            return ("cmd", name)
        if name == "{":
            inner = self.parse_seq({"\\}"}, set_mode=True)
            if self.peek() is not None and self.peek().text == "\\}":
                self.i += 1
            return ("set", inner)
        if name == "}":
            return ("drop",)
        return ("cmd", name)

    def parse_left(self):
        d1 = self.toks[self.i].text if self.peek() else "."
        self.i += 1
        inner = self.parse_seq({"\\right"}, set_mode=(d1 == "\\{"))
        d2 = "."
        if self.peek() is not None and self.peek().text == "\\right":
            self.i += 1
            if self.peek() is not None:
                d2 = self.peek().text
                self.i += 1
        if d1 == "|":
            return ("abs", inner)
        if d1 == "‖":
            return ("norm", inner)
        if d1 == "\\{":
            return ("set", inner)
        if d1 == "\\lfloor":
            return ("acc", "floor", inner)
        if d1 == "\\lceil":
            return ("acc", "ceil", inner)
        if d1 == "\\langle":
            return ("paren", "⟨", "⟩", inner)
        if d1 in ("(", "["):
            return ("paren", d1, d2 if d2 in (")", "]") else ")", inner)
        return ("group", inner)

    def parse_env(self):
        name = self.parse_raw_arg().strip()
        if name in ("array", "tabular"):
            self.parse_raw_arg()  # column spec
        depth, j = 1, self.i
        while j < len(self.toks):
            t = self.toks[j]
            if t.kind == "cmd" and t.text == "\\begin":
                depth += 1
            elif t.kind == "cmd" and t.text == "\\end":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = self.toks[self.i:j]
        self.i = min(j + 1, len(self.toks))
        self.parse_raw_arg()  # {name} of \end
        rows, row, cell, braces, nest = [], [], [], 0, 0
        for t in body:
            if t.kind == "sym" and t.text == "{":
                braces += 1
            elif t.kind == "sym" and t.text == "}":
                braces -= 1
            elif t.kind == "cmd" and t.text == "\\begin":
                nest += 1
            elif t.kind == "cmd" and t.text == "\\end":
                nest -= 1
            if braces == 0 and nest == 0 and t.kind == "sym" and t.text == "&":
                row.append(cell)
                cell = []
            elif braces == 0 and nest == 0 and t.kind == "cmd" and t.text == "\\\\":
                row.append(cell)
                rows.append(row)
                row, cell = [], []
            else:
                cell.append(t)
        if cell or row:
            row.append(cell)
            rows.append(row)
        parsed = [[_Parser(self.src, c).parse_seq() for c in r] for r in rows]
        parsed = [r for r in parsed if any(r)]
        return ("env", name, parsed)

    @staticmethod
    def _fix_bars(nodes: list, set_mode: bool) -> list:
        idx = [i for i, n in enumerate(nodes) if n[0] == "sym" and n[1] in ("|", "‖")]
        if not idx:
            return nodes
        if set_mode or len(idx) % 2:
            return [("cmd", "mid") if i in idx else n for i, n in enumerate(nodes)]
        out, i, pairs = [], 0, dict(zip(idx[::2], idx[1::2]))
        while i < len(nodes):
            if i in pairs:
                j = pairs[i]
                out.append(("abs" if nodes[i][1] == "|" else "norm", nodes[i + 1:j]))
                i = j + 1
            else:
                out.append(nodes[i])
                i += 1
        return out


class LatexSpeaker:
    def __init__(self, normalizer):
        self.n = normalizer
        self.in_lim = False

    @property
    def lex(self):
        return self.n.lexicon

    def speak(self, src: str) -> Optional[str]:
        try:
            toks = _tokenize(src, self.n.lang.decimal_sep == ",")
            tree = _Parser(src, toks).parse_seq()
            text = self.seq(tree)
        except Exception:  # malformed or unsupported input: caller keeps the original
            return None
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    # ------------------------------------------------------------------ helpers
    def phrase(self, key: str, **kw) -> str:
        return self.lex.phrases[key].format(**kw)

    def _simple(self, nodes: list) -> bool:
        if len(nodes) == 1:
            return nodes[0][0] in ("num", "let", "cmd")
        return (len(nodes) == 2 and nodes[0] == ("sym", "-") and nodes[1][0] in ("num", "let"))

    @staticmethod
    def _is_op(node) -> bool:
        if node[0] == "sym":
            return node[1] in "+-=<>,;:/*|‖±×÷≠≤≥≈−"
        return node[0] == "cmd" and node[1] in _OPERATOR_CMDS

    def _is_func(self, node) -> bool:
        base = node[1] if node[0] == "script" else node
        if base[0] == "cmd":
            return base[1] in self.lex.latex_functions
        return base[0] == "let" and base[1] in _FUNC_LETTERS and (
            node[0] != "script" or node[2] is None and node[3] is None)

    @staticmethod
    def _join(parts) -> str:
        out: List[str] = []
        for p in parts:
            if not p:
                continue
            if p in (",", ";", ".", "!", "?") and out:
                out[-1] += p
            else:
                out.append(p)
        return " ".join(out)

    # ------------------------------------------------------------------ render
    def seq(self, nodes: list) -> str:
        nodes = [x for x in nodes if x[0] != "drop"]
        parts: List[str] = []
        i, n = 0, len(nodes)
        while i < n:
            node = nodes[i]
            prev = nodes[i - 1] if i else None
            nxt = nodes[i + 1] if i + 1 < n else None
            k = node[0]
            if k == "sym" and node[1] == "!" and prev is not None and not self._is_op(prev) \
                    and parts and nxt != ("sym", "="):
                parts[-1] = self.phrase("factorial", x=parts[-1])
            elif k == "text" and prev is not None and prev[0] == "num" \
                    and self._unit(node[1]) is not None:
                form, per = self._unit(node[1])
                digits = _decimal(prev[1])
                ip, sep, fp = digits.partition(".")
                parts[-1] = self.n._words(ip, fp if sep else None, False, form.gender)
                parts.append(form.pick(digits == "1"))
                if per is not None:
                    parts.append(f"{self.n.lang.per_word} {per.singular}")
            elif nxt is not None and nxt[0] == "paren" and nxt[1] == "(" and self._is_func(node):
                parts.append(self.phrase("of", f=self.node(node), x=self.seq(nxt[3])))
                i += 1
            elif k == "paren":
                inner = self.seq(node[3])
                wrap = (prev is not None and not self._is_op(prev)) or \
                       (nxt is not None and not self._is_op(nxt))
                parts.append(self._wrap(node, inner) if wrap else inner)
            else:
                parts.append(self.node(node))
            i += 1
        return self._join(parts)

    def _unit(self, text: str):
        r"""``(form, per_form)`` for a unit in ``\mathrm{...}`` after a number, else None.

        Understands ``m/s^2`` and ``N\cdot m``. In math a lone capital is a unit (``300\,\mathrm{K}``),
        including bases that prose only knows with a prefix (K, A, C, F, T).
        """
        u = re.sub(r"\^\{?([23])\}?", lambda m: "²" if m.group(1) == "2" else "³", text)
        u = re.sub(r"\s*\\cdot\s*", "·", u).strip()
        lex = self.lex

        def find(sym: str):
            return lex.units.get(sym) or lex.prefix_bases.get(sym)

        num, slash, den = u.partition("/")
        form = find(num.strip())
        if form is None:
            return None
        if not slash:
            return form, None
        per = find(den.strip())
        return (form, per) if per is not None else None

    def _wrap(self, node, inner: str) -> str:
        o = _OPEN_PHRASE.get(node[1])
        c = _CLOSE_PHRASE.get(node[2])
        left = self.phrase(o) if o else ""
        right = self.phrase(c) if c else ""
        return " ".join(p for p in (left, inner, right) if p)

    def num(self, text: str) -> str:
        ip, sep, fp = _decimal(text).partition(".")
        return self.n._words(ip, fp if sep else None, False)

    def sym(self, x: str) -> str:
        lex = self.lex
        if x in lex.latex_commands:
            return lex.latex_commands[x]
        if x in lex.symbols and x not in "#&%^":
            return lex.symbols[x]
        if x == "-":
            return lex.symbols.get("−", "-")
        if x in ",;.!?":
            return x
        if x in "~&^_$`\"#(){}[]":
            return ""
        if x == "%":
            return lex.symbols.get("%", "%")
        if x == "'":
            return self.phrase("prime")
        return x

    def cmd(self, name: str) -> str:
        lex = self.lex
        if self.in_lim and name in ("to", "rightarrow"):
            return self.phrase("approaches")
        word = lex.latex_commands.get("\\" + name)
        if word is not None:
            return word
        if name in GREEK:
            return GREEK[name]
        if name in lex.latex_functions:
            return lex.latex_functions[name]
        if name in _BIGOPS:
            return self._bigop(name, None, None)
        return name if name.isalpha() else ""

    def node(self, node) -> str:
        k = node[0]
        if k == "num":
            return self.num(node[1])
        if k == "let":
            return node[1]
        if k == "sym":
            return self.sym(node[1])
        if k == "cmd":
            return self.cmd(node[1])
        if k == "group":
            return self.seq(node[1])
        if k == "paren":
            return self.seq([node])
        if k == "script":
            return self.script(node)
        if k == "frac":
            return self.frac(node[1], node[2])
        if k == "binom":
            return self.phrase("binom", n=self.seq(node[1]), k=self.seq(node[2]))
        if k == "sqrt":
            return self.sqrt(node[1], node[2])
        if k in ("abs", "norm"):
            inner = self.seq(node[1])
            return self.phrase(k if self._simple(node[1]) else k + "_complex", x=inner)
        if k == "acc":
            return self.phrase(node[1], x=self.seq(node[2]))
        if k == "set":
            return self.phrase("set", x=self.seq(node[1]))
        if k == "text":
            return self.n._plain(node[1]).strip()
        if k == "bb":
            key = "bb_" + node[1]
            return self.lex.phrases[key] if key in self.lex.phrases else node[1]
        if k == "env":
            return self.env(node[1], node[2])
        return ""

    def frac(self, a: list, b: list) -> str:
        if len(a) == 1 and len(b) == 1 and a[0][0] == "num" and b[0][0] == "num" \
                and a[0][1].isdigit() and b[0][1].isdigit() and a[0][1] != "0" * len(a[0][1]) \
                and int(b[0][1]) > 1:
            return self.n.lang.fraction(int(a[0][1]), int(b[0][1]))
        key = "frac" if self._simple(a) and self._simple(b) else "frac_complex"
        return self.phrase(key, a=self.seq(a), b=self.seq(b))

    def sqrt(self, index, x: list) -> str:
        body = self.seq(x)
        suffix = "" if self._simple(x) else "_complex"
        if index is None or index == [("num", "2")]:
            return self.phrase("sqrt" + suffix, x=body)
        if index == [("num", "3")]:
            return self.phrase("cube_root" + suffix, x=body)
        if len(index) == 1 and index[0][0] == "num" and index[0][1].isdigit():
            return self.phrase("root" + suffix, ord=self.n.lang.ordinal(int(index[0][1])), x=body)
        return self.phrase("root_general" + suffix, n=self.seq(index), x=body)

    def _bigop(self, name: str, sub, sup) -> str:
        key = _BIGOPS[name]
        op = self.phrase("op_" + key)
        if sub is None:
            return self.phrase("bigop", op=op)
        was, self.in_lim = self.in_lim, key == "lim"
        try:
            lo = self.seq(sub)
        finally:
            self.in_lim = was
        if key == "lim":
            return self.phrase("bigop_lim_lo", op=op, lo=lo)
        if sup:
            return self.phrase("bigop_lohi", op=op, lo=lo, hi=self.seq(sup))
        return self.phrase("bigop_lo", op=op, lo=lo)

    def script(self, node) -> str:
        _, base, sub, sup, primes = node
        if base[0] == "cmd" and base[1] in _BIGOPS:
            return self._bigop(base[1], sub, sup)
        if base[0] == "paren":
            b = self._wrap(base, self.seq(base[3]))
        else:
            b = self.node(base)
        if base[0] == "cmd" and base[1] in self.lex.latex_functions and sub:
            if base[1] == "log":
                b = self.phrase("log_base", b=self.seq(sub))
            else:
                b = self.phrase("fn_lo", fn=b, lo=self.seq(sub))
        elif sub:
            b = self.phrase("sub", b=b, i=self.seq(sub))
        if primes:
            b = f"{b} " + self.phrase(("prime", "double_prime", "triple_prime")[min(primes, 3) - 1])
            if primes > 3:
                b = f"{b} " + " ".join([self.phrase("prime")] * (primes - 3))
        if not sup:
            return b
        if len(sup) == 1 and sup[0] == ("cmd", "circ"):
            return f"{b} " + self.phrase("degrees")
        if sup == [("num", "2")]:
            return self.phrase("sq", b=b)
        if sup == [("num", "3")]:
            return self.phrase("cube", b=b)
        if len(sup) == 1 and sup[0][0] == "num" and sup[0][1].isdigit() and 4 <= int(sup[0][1]) < 1000:
            k = int(sup[0][1])
            return self.phrase("pow_int", b=b, ord=self.n.lang.ordinal(k), card=self.n.lang.cardinal(k))
        key = "pow" if self._simple(sup) else "pow_complex"
        return self.phrase(key, b=b, e=self.seq(sup))

    def env(self, name: str, rows: list) -> str:
        def cells(row, sep):
            return sep.join(c for c in (self.seq(cell) for cell in row) if c)

        if name in _MATRIX_ENVS:
            body = "; ".join(
                self.phrase("row", i=self.n.lang.cardinal(i), cells=cells(r, ", "))
                for i, r in enumerate(rows, 1))
            return self.phrase("matrix", rows=body)
        body = "; ".join(cells(r, " ") for r in rows)
        if name == "cases":
            return self.phrase("cases", rows=body)
        return body


# ---------------------------------------------------------------- bare LaTeX (no delimiters)
_CMD_RE = re.compile(r"\\([A-Za-z]+)")
_DIGITS_RE = re.compile(r"\d+(?:\.\d+)?")
_LETTERS_RE = re.compile(r"[A-Za-z]+")
_BARE_OPS = frozenset("+-*/=<>()[]")
_STRUCTURE = (
    {"frac", "dfrac", "tfrac", "cfrac", "binom", "dbinom", "tbinom", "sqrt", "mathbb", "left",
     "right", "lfloor", "rfloor", "lceil", "rceil", "langle", "rangle", "prime"}
    | set(_ACCENTS) | _TEXTLIKE | _STYLE | set(_BIGOPS)
)


def _known(name: str, lex) -> bool:
    return ("\\" + name in lex.latex_commands or name in lex.latex_functions
            or name in GREEK or name in _STRUCTURE)


def _brace_match(text: str) -> dict:
    """``{`` index -> index of its ``}`` (only for balanced pairs on one line); linear time."""
    match, stack, i, n = {}, [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            stack.append(i)
        elif c == "}" and stack:
            match[stack.pop()] = i
        elif c == "\n":
            stack.clear()
        i += 1
    return match


def find_bare(text: str, lex) -> List[tuple]:
    """Runs of LaTeX outside math delimiters, as ``(start, end, speakable)`` triples.

    A run starts at ``\name`` when the command is known to the lexicon (or is any command
    directly followed by ``{``, which is protected but never spoken) and extends over balanced
    ``{}`` groups, scripts, further known commands, digits, single letters, simple operators
    and blanks. It stops before a word of two or more letters, a sentence mark, a newline or
    any other character. A run containing unbalanced braces is kept whole but not speakable.
    """
    if "\\" not in text:
        return []
    match = _brace_match(text)
    runs, pos, n = [], 0, len(text)
    for m in _CMD_RE.finditer(text):
        start = m.start()
        if start < pos or (start and text[start - 1] == "\\"):
            continue
        known = _known(m.group(1), lex)
        if not known and text[m.end():m.end() + 1] != "{":
            continue
        last = j = m.end()
        prev, bad = "cmd", False
        while j < n:
            ch = text[j]
            if ch == "{":
                if j != last and not (known and prev == "script"):
                    break
                if prev not in ("cmd", "grp", "script"):
                    break
                if j in match:
                    j = last = match[j] + 1
                    prev = "grp"
                else:  # unbalanced: keep scanning, but the run is verbatim only
                    bad = True
                    j = last = j + 1
                    prev = "op"
            elif not known:
                break
            elif ch == "}":
                bad = True
                j = last = j + 1
                prev = "op"
            elif ch in "^_":
                if prev == "script":
                    break
                j += 1
                prev = "script"
            elif ch == "\\":
                cm = _CMD_RE.match(text, j)
                if not cm or not _known(cm.group(1), lex):
                    break
                j = last = cm.end()
                prev = "cmd"
            elif ch.isdigit():
                j = last = _DIGITS_RE.match(text, j).end()
                prev = "atom"
            elif "A" <= ch <= "z" and ch.isalpha():
                w = _LETTERS_RE.match(text, j)
                if w.end() - j > 1:
                    break
                j = last = w.end()
                prev = "atom"
            elif ch in _BARE_OPS:
                j = last = j + 1
                prev = "op"
            elif ch in " \t":
                j += 1
            else:
                break
        while last > m.end() and text[last - 1] in "+-*/=<>":
            last -= 1
        runs.append((start, last, known and not bad))
        pos = last
    return runs
