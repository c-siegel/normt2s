# normt2s

[![PyPI](https://img.shields.io/pypi/v/normt2s)](https://pypi.org/project/normt2s/)
[![Python](https://img.shields.io/pypi/pyversions/normt2s)](https://pypi.org/project/normt2s/)
[![License: MIT](https://img.shields.io/pypi/l/normt2s)](LICENSE)

**Make written text speakable.** `normt2s` turns numbers, units, abbreviations, dates, formulas and
math into the words a text-to-speech engine should say, so `3.5 km/h` is not read as "three dot
five k m slash h".

- English and German, no dependencies, pure Python 3.9+
- About 55 µs for a typical sentence
- Built for LLM output: streaming token by token, optional Markdown stripping, your own control
  tokens and user pronunciation rules

```python
from normt2s import normalize

normalize("It costs $3.50 for 2 kg, e.g. in 1984.")
# 'It costs three dollars and fifty cents for two kilograms, for example in nineteen eighty-four.'

normalize("Der Zug fährt 120 km/h, z. B. um 14:30.", lang="de")
# 'Der Zug fährt einhundertzwanzig Kilometer pro Stunde, zum Beispiel um vierzehn Uhr dreißig.'
```

## Contents

[Install](#install) · [What gets converted](#what-gets-converted) ·
[Adding your own words](#adding-your-own-words) · [Markdown](#markdown) ·
[Control tokens](#your-own-control-tokens) · [Rule sets](#rule-sets-for-pronunciations) ·
[Math](#math-latex) · [Streaming](#streaming-llm-output) · [API reference](#reference-options-and-api) ·
[How it works](#how-it-works) · [Adding a language](#adding-a-language) ·
[Performance](#performance) · [Limitations](#known-limitations) · [Development](#development)

## Install

```
pip install normt2s
```

From a clone of the repository: `pip install -e .`

## What gets converted

Every row is real output from the library.

### English

| Category | Input | Spoken |
|---|---|---|
| Numbers | `1,234 points`, `1 000 points` | one thousand two hundred thirty-four points, one thousand points |
| | `3.14`, `-5`, `007` | three point one four, minus five, zero zero seven |
| | `1st`, `23rd`, `50%`, `1/2 cup` | first, twenty-third, fifty percent, one half cup |
| Years | `in 1984`, `the 1990s` | in nineteen eighty-four, the nineteen nineties |
| | `I have 1984 apples` | I have one thousand nine hundred eighty-four apples |
| Time | `3:45 pm`, `at 14:30` | three forty-five p m, at fourteen thirty |
| Dates | `March 3rd, 2024`, `2024-03-15` | March third, twenty twenty-four; March fifteenth, twenty twenty-four |
| Units | `100 km/h`, `20°C`, `9.81 m/s²`, `1 ft` / `2 ft` | one hundred kilometers per hour, twenty degrees Celsius, nine point eight one meters per second squared, one foot / two feet |
| Currency | `$3.50`, `€5`, `5 EUR`, `$2.5 million` | three dollars and fifty cents, five euros, five euros, two point five million dollars |
| Abbreviations | `Dr. Smith, e.g. ...`, `etc.` | Doctor Smith, for example ..., et cetera |
| Math symbols | `2 + 3 = 5`, `x²`, `a ≤ b` | two plus three equals five, x squared, a is less than or equal to b |
| Operators | `3 * 4 * 5`, `2*(x+1)`, `3 / 4` | three times four times five, two times (x plus one), three divided by four |
| Chemistry | `H2O`, `CO2`, `U-235` | H two O, C O two, U two hundred thirty-five |
| Pauses | `The result — a success — was clear.` | The result, a success, was clear. |

### German

| Category | Input | Spoken |
|---|---|---|
| Numbers | `1.234,15`, `1/3`, `3/4` | eintausendzweihundertvierunddreißig Komma eins fünf, ein drittel, drei viertel |
| Ordinals | `der 3. Platz`, `im 21. Jahrhundert`, `Kapitel 3. Danach` | der dritte Platz, im einundzwanzigsten Jahrhundert, Kapitel drei. Danach |
| Dates | `15.03.2024`, `am 15.03.2024` | fünfzehnter März zweitausendvierundzwanzig, am fünfzehnten März zweitausendvierundzwanzig |
| | `am 3. Mai`, `im Mai 2024` | am dritten Mai, im Mai zweitausendvierundzwanzig |
| Time | `um 14:30`, `um 14:30 Uhr` | um vierzehn Uhr dreißig |
| Units | `1 kg`, `1 min`, `21 min` | ein Kilogramm, eine Minute, einundzwanzig Minuten |
| Number + unit word | `1 Stunde`, `1 Kilogramm`, `21 Stunden` | eine Stunde, ein Kilogramm, einundzwanzig Stunden |
| Currency | `3,50 €`, `5 €` | drei Euro fünfzig Cent, fünf Euro |
| Abbreviations | `z. B.`, `ca. 5 Mio.` | zum Beispiel, circa fünf Millionen |

German dates take their case ending from the word before: `am` / `vom` / `zum` / `dem` / `den` give
*fünfzehnten*, `der` gives *fünfzehnte*, a date on its own gives *fünfzehnter*.

### Details

- **Symbols:** `add_symbol` accepts any character or sequence without whitespace
  (`n.add_symbol("@", "at")`); an empty or blank key raises `ValueError`.
- **`*` and `/`** are ambiguous in prose, so they live in an `operators` table and are only read
  between operands: `3 * 4`, `3*4` and `2*(x+1)` use "times"; `3 / 4` (spaces required) uses "divided
  by". `1/2` stays a fraction; `a * b`, `*word*` and `and/or` are untouched. `·` also takes single
  letters: `F = m · a` is "F equals m times a", while `Lehrer·innen` and `Home · About` are untouched.
- **Spelled tokens:** `CO2` would be read as one made-up word, so listed formulas are spelled out
  (letters as themselves, digit runs as numbers; `CO_2` matches too). Built in: `CO2 H2O O2 O3 N2 H2
  CH4 NH3 NaCl H2SO4 HCl NaOH CaCO3 SO2 NO2 C6H12O6`. Add more with `n.add_spelled("ATP5")`. Matching
  is whole-token: `ECO2000` and `CO23` are left alone. Isotopes (`U-235`: element symbol, hyphen,
  1–3 digits) lose the hyphen; `A-4` is not an element and stays.
- **Pauses:** an em dash becomes a comma pause, and between digits a range (`10—20` is "ten to
  twenty"). A dash at a line edge is dropped. Change it with `n.add_punctuation(char, replacement)`.
- **Left alone:** code (inline and fenced), URLs, e-mail addresses, HTML tags and Markdown link
  targets. So are things that only look like numbers: `3.2.1` is read digit by digit and `mp3` is
  not split.

## Adding your own words

**Create a `Normalizer`, add words to it, and use that instance.**

```python
from normt2s import Normalizer, normalize

n = Normalizer("en")
n.add_abbreviation("LOLA", "Lola")
n.add_unit("kn", "knot")                                      # plural defaults to "knots"
n.add_unit("ch", "child", "children")                         # or give the plural yourself
n.add_currency("CHF", ("franc", "francs"), ("rappen", "rappen"))

n.normalize("LOLA sails 12 kn with 2 ch for 5.20 CHF")
# 'Lola sails twelve knots with two children for five francs and twenty rappen'

normalize("LOLA sails 12 kn", n)       # the helper also accepts your instance
```

> **Gotcha:** `normalize(text, "en")` uses a separate, shared instance. Words added to your own
> `Normalizer("en")` are not visible there. Pass your instance, or edit the shared one with
> `get_normalizer("en")`.

Your entries override the built-in ones and apply immediately, even to an instance you have already
used.

| You want to change | Method | Example |
|---|---|---|
| An abbreviation | `add_abbreviation(key, to)` | `("tbh", "to be honest")` |
| A unit after a number | `add_unit(symbol, singular, plural, gender)` | `("kn", "knot")` |
| SI-prefixed units of a base | `add_prefixed_unit(base, prefixes, singular=None, ...)` | `("Pa", "hkM")` |
| A currency | `add_currency(symbol, major, minor)` | see above |
| A symbol (any character or sequence) | `add_symbol(key, word)` | `("=", "is")`, `("!=", "is not")` |
| `*`, ` / ` or `·` between operands | `lexicon.add_operator(key, word)` | `("*", "times")` |
| A token spelled letter by letter | `add_spelled(token)` | `("ATP5")` |
| A character read as a pause | `add_punctuation(char, replacement)` | `("—", ", ")` |
| Text to keep or drop | `add_protected(pattern, spoken=None, opener=None)` | `(r"::[a-z_]+::")` |
| A LaTeX command / function / template | `lexicon.add_latex_command(name, spoken)`, `add_latex_function`, `add_phrase` | `("R", "the reals")` |
| Remove an entry | `lexicon.remove(kind, key)` | `("abbreviations", "vs.")` |

Abbreviations: matching is case sensitive, but a capitalised variant is added for lowercase keys
(`e.g.` also gives `E.g.`; `capitalized=False` turns that off). Spaces inside a key are optional
(`z. B.` matches `z.B.`). Use `final=True` for abbreviations that can end a sentence (`etc.`), so the
full stop is kept before a new sentence.

### Using a file

`n.load_lexicon("my_terms.json")` (or `.toml` on Python 3.11+) with the same format as the built-in
data in [en.json](src/normt2s/data/en.json) and [de.json](src/normt2s/data/de.json):

```json
{
  "abbreviations": {"LMS": "learning management system", "etc.": {"to": "et cetera", "final": true}},
  "units": {"kn": ["knot"], "ch": ["child", "children"]},
  "prefixed_units": {"Pa": "hkM", "Wb": ["m", "weber"]},
  "currencies": {"CHF": {"major": ["franc", "francs"], "minor": ["rappen", "rappen"]}},
  "symbols": {"=": "equals"},
  "operators": {"*": "times", "/": "divided by"},
  "spelled": ["ATP5"],
  "punctuation": {"—": ", "},
  "protected": [{"pattern": "\\[\\d+\\]", "spoken": ""}, "::[a-z_]+::"],
  "latex": {
    "commands": {"R": "the reals"},
    "functions": {"sinc": "sinc"},
    "phrases": {"frac": "{a} divided by {b}"}
  }
}
```

A unit entry is `[singular, plural, gender]`; plural and gender are optional, and the gender
(`"m"`, `"f"`, `"n"`) only matters in German.

**SI prefixes.** Prefixed units are generated from a base and the prefixes it takes, so `µF`, `hPa`,
`MΩ`, `mSv` or `keV` need no entry each. The word is prefix + base, with gender and plural from the
base: `10 µF` is "zehn Mikrofarad", `1 TWh` "eine Terawattstunde". Each base lists only its common
prefixes, so `Mm` and `cd` are not units. A base given as a string must be a unit (`"Pa": "hkM"`);
one given as `[prefixes, singular, plural, gender]` need not be, so `µF` is read but a bare `5F` is
not farads. `µ` also matches the Greek `μ`, and units added with `add_unit` always win. The prefix
words live in `"prefixes"` (`n.lexicon.add_prefix("Q", "quetta")`).

## Markdown

LLM replies are Markdown, and read aloud `**`, `#` or `[text](url)` are noise. Opt in with
`markdown="strip"`:

```python
n = Normalizer("en", markdown="strip")
n.normalize("## Plan\n- **Walk** 3*4 km, see [the map](https://example.com/a_b)")
# 'Plan\nWalk three times four kilometers, see the map'
```

| Construct | Input | Spoken text |
|---|---|---|
| Bold, italic, strike-through | `**a**`, `__a__`, `*a*`, `_a_`, `~~a~~` | `a` (italics only if the content has a letter) |
| Heading, quote | `## Title`, `> text` | `Title`, `text` |
| Lists | `- item`, `* item`, `+ item`, `1. item`, `1) item` | `item` |
| Rule | `---`, `***`, `___`, `* * *` (own line) | empty line |
| Link, image | `[text](url)`, `![alt](url)` | `text`, `alt` |
| Inline / fenced code | `` `x = 1` ``, ```` ```python\ncode\n``` ```` | the code, verbatim; the language label is dropped |

Code, URLs, e-mail, HTML and math are masked first, so `snake_case_name`, `` `a*b*c` `` and
`$a_1 * b_1$` are safe and `3*4*5` is not taken for emphasis. In a stream, an unclosed `**`, `__`,
`~~`, `*x`, `_x` or `[text](` is held back until it closes or the line ends.

Not handled: tables, footnotes, reference-style links. A line starting with a number and a dot
(`3. Mai war schön`) is a list item in Markdown and loses the number.

## Your own control tokens

Applications put their own markers into LLM output: `[laughs]`, `::wave::`, `<emotion:happy>`,
citation numbers `[1]`. They must not be normalized or cut in half by a stream, and are often meant
to be dropped from speech but kept for display:

```python
n.add_protected(r"::[a-z_]+::")              # kept verbatim in the spoken text
n.add_protected(r"\[\d+\]", spoken="")       # removed from the spoken text, kept in Piece.raw

n.normalize("Hi ::wave:: it is 5 km [1] away.")
# 'Hi ::wave:: it is five kilometers away.'
```

- `spoken=None` keeps a match, `""` removes it (and the doubled space it leaves), any other string
  replaces it.
- A protected match separates a number from its unit like any other protected span:
  `5 ::wave:: kg` is "five ::wave:: kg".
- The pattern is a regular expression written by *you*: it must compile, not match the empty string
  and have no capturing groups (use `(?:...)`), else `ValueError`.
- A stream never cuts inside a match. For a match that has started but is not complete (`::wav`) it
  uses the pattern's literal start (`::`), taken from the pattern when possible (leading `^`, `\b`
  and lookarounds are skipped). Otherwise pass `opener="..."`, or `opener=""` if matches can never
  contain a sentence end.

`::[a-z_]+::` also matches inside code such as `std::vector::size`, so with `spoken=""` that would be
read as "std size". Guard the marker so it only stands on its own:

```python
n.add_protected(r"(?<![\w:])::[a-z_]+::(?![\w:])", spoken="")
n.normalize("Call std::vector::size ::wave:: now")   # 'Call std::vector::size now'
```

## Rule sets for pronunciations

Applications let users fix pronunciations: `pH` should be "p H", `{number} kg` should be "{number}
kilograms". Replacing before the normalizer breaks grammar (German `1 Kilogramm` would be "eins
Kilogramm"); replacing after it misses because numbers are already words. A `RuleSet` runs inside
the pipeline:

```python
from normt2s import Normalizer, Rule, RuleSet

rules = RuleSet([
    Rule("pH", "p H", case_sensitive=True),
    Rule("{number} kg", "{number} Kilogramm"),
    Rule("{number} Std.", "{number} Stunde", gender="f", plural="Stunden"),
    Rule("Δ", "Delta", whole_word=False),
])
n = Normalizer("de")
n.normalize("1 kg bei pH 7", rules=rules)          # 'ein Kilogramm bei p H sieben'

applied = []
n.normalize("pH 7", rules=rules, applied=applied)  # applied == [Rule("pH", "p H", ...)]
```

`Rule(term, spoken, whole_word=True, case_sensitive=False, gender=None, plural=None,
renormalize=False)` is a frozen
dataclass. A `RuleSet` is immutable and hashable by content, so cache one per user with
`functools.lru_cache`; one shared `Normalizer` per language serves any number of rule sets and is
never changed by them. `stream(rules=...)`, `normalize_stream(chunks, rules=...)` and
`normalize(text, "en", rules)` take rules too. Load them with
`RuleSet.from_dicts([{"term": ..., "spoken": ...}])` or `RuleSet.load("rules.json")`
(`{"rules": [...]}`); camelCase keys (`caseSensitive`, `wholeWord`) are accepted.

How terms match:

- A term is **literal text**, never a regex. A space matches any run of whitespace (`e. g.` also
  matches across a line break).
- `{number}` matches `5`, `1,5`, `3.000,25` or `1,234.5` (with a leading minus), may appear several
  times, and is replaced in `spoken` by the number in words, in order.
- `whole_word=True` stops a rule matching inside a word: `N` does not match in `Newton`, but `kg`
  matches in `10kg`. Terms starting or ending with a symbol (`°C`) need no guard.
- The longest term wins, then plain before template, then case-sensitive before case-insensitive.
  Text is scanned once from left to right and a replacement is never matched again. A replacement
  touching a letter or digit is padded with a space (`Δt` is "Delta t").
- The word after `{number}` is looked up among the units: its gender is used for the number (`1 kg`
  is "ein Kilogramm") and singular or plural follows the value (`21 min` is "einundzwanzig Minuten").
  `gender=` and `plural=` override this. For a German noun that is not a unit, pass `gender=`
  (`"m"`, `"f"` or `"n"`), else `1` is read "eins".
- A replacement is not normalized again: `Rule("1 s", "1 Sekunde")` gives "1 Sekunde". Pass
  `renormalize=True` to read it once more (without rules): "eine Sekunde".
- Empty terms are ignored. Terms over 200 characters or more than 2,000 rules raise `ValueError`.

## Math (LaTeX)

Math in `$...$`, `$$...$$`, `\(...\)` and `\[...\]` is read aloud:

```python
normalize(r"The area is $\pi r^2$.")
# 'The area is pi r squared.'

normalize(r"Solve $\frac{a+b}{c} = \sqrt{x}$ now")
# 'Solve the fraction a plus b over c, end fraction equals square root of x now'

normalize(r"Es gilt $x \in \mathbb{R}$ und $\sum_{i=1}^{n} i$.", lang="de")
# 'Es gilt x ist Element von den reellen Zahlen und die Summe von i gleich eins bis n über i.'
```

Supported: fractions, roots, powers and subscripts, sums, products, integrals, limits, Greek
letters, relations and set notation, functions (`\sin`, `\log`), absolute values, norms, accents,
`\binom`, factorials, primes, matrices, `cases`, `\text{}` / `\mathrm{}`. Units after a number work:
`5\,\mathrm{km}` is "five kilometers".

- **Parentheses** are only spoken where they change the meaning: `(a+b)^2` and `2(x+1)` get "open
  paren ... close paren", `y = (x+1)` does not. Complex arguments are fenced ("the square root of x
  plus one, end root").
- **Malformed LaTeX** never raises and is left as written. A single `$` only starts math under the
  pandoc rule, so `from $5 to $6` stays currency.
- **Bare LaTeX** (no `$...$`) such as `\frac{1}{2}` or `a \cdot b` is protected by default, so its
  numbers are not rewritten. `Normalizer("en", latex_bare="speak")` reads it like delimited math. A
  run starts at a known command and stops before a word, a sentence mark or a newline; unknown
  commands (`C:\Users\name`) and unbalanced braces are left alone.
- `Normalizer("en", latex="keep")` leaves all math untouched.
- `add_latex_command` is for symbol-like names (`\cdot`), `add_latex_function` for names applied to
  an argument (`\sinc x`). Commands win when both exist; `add_latex_function` warns then.

## Streaming LLM output

You cannot normalize LLM tokens one by one (`"1"`, `"20"`, `" km"` would be read separately). The
stream wrapper buffers text and releases it only when that is safe:

```python
stream = n.stream()
for token in llm_tokens:
    speakable = stream.feed(token)     # "" until a safe boundary is reached
    if speakable:
        tts.say(speakable)
tts.say(stream.flush())                # call once at the end

for speakable in n.normalize_stream(llm_tokens):   # or as a generator
    tts.say(speakable)
```

```
feed 'The train '   -> ''
feed 'goes 1'       -> ''
feed '20 km'        -> ''
feed '/h. Dr'       -> 'The train goes one hundred twenty kilometers per hour. '
feed '. Smith '     -> ''
feed 'pays $3'      -> ''
feed '.50 now'      -> ''
feed '. Done'       -> ''
flush               -> 'Doctor Smith pays three dollars and fifty cents now. Done'
```

Text is released at the end of a sentence or at a newline, never inside a number and its unit, an
abbreviation, a date, a code block, a math span or a protected token. The joined output is identical
to normalizing the whole text at once, whatever the chunking (tested). A long run without a boundary
is flushed after `max_buffer` characters (default 400) at a whitespace that does not follow a number
or a word that binds one (`in 1984`, `am 15.03.`). The trade-off: speech starts at the end of the
first sentence, not at the first token.

**Chunk sizes.** For a voice UI that wants early audio and longer chunks later:

```python
stream = n.stream(first_min_chars=25, min_chars=80, max_buffer=300)
```

The first chunk ends at the first boundary at least `first_min_chars` long; later chunks end at the
last boundary, once it is at least `min_chars` long (otherwise the stream waits). `flush()` releases
everything. The defaults (`0`, `0`) release up to the last boundary as soon as possible. A large token
can release several chunks at once; `feed()` returns them joined.

**Raw and spoken together.** A chat UI shows the original text and speaks the normalized text.
`feed_pieces()` returns `Piece(raw, spoken)` tuples:

```python
for piece in stream.feed_pieces(token):   # a list: zero or more pieces
    show(piece.raw)
    speak(piece.spoken)
last = stream.flush_piece()               # Piece, or None if nothing was buffered
```

The `raw` parts join to exactly the input and the `spoken` parts to exactly `normalize(input)`. A
piece with empty `spoken` (only Markdown markers, a dropped `[1]`) is still returned, so `raw` is
never lost. `normalize_stream` yields one `spoken` string per piece.

## Reference: options and API

```python
Normalizer(lang="en", lexicon=None, latex="speak", latex_bare="protect", markdown="keep")
```

| Argument | Meaning |
|---|---|
| `lang` | `"en"` or `"de"` (or a `Language` object) |
| `lexicon` | a `Lexicon` to use instead of the built-in data |
| `latex` | `"speak"` (default) reads math aloud, `"keep"` leaves it untouched |
| `latex_bare` | LaTeX outside math delimiters: `"protect"` (default) keeps it, `"speak"` reads it |
| `markdown` | `"keep"` (default) or `"strip"` |

| Call | What it does |
|---|---|
| `normalize(text, lang="en", rules=None)` | one-shot helper; `lang` is a code or your own `Normalizer` |
| `get_normalizer(lang)` | the shared instance behind `normalize(text, "en")` |
| `n.normalize(text, rules=None, applied=None)` (or `n(text)`) | normalize a string |
| `n.stream(max_buffer=400, first_min_chars=0, min_chars=0, rules=None)` | a `StreamNormalizer`: `feed()`, `flush()`, `feed_pieces()`, `flush_piece()` |
| `n.normalize_stream(chunks, max_buffer=400, first_min_chars=0, min_chars=0, rules=None)` | generator of spoken chunks |
| `Rule`, `RuleSet`, `Piece` | rules and stream pieces (see above) |
| `n.add_*`, `n.load_lexicon(path)`, `n.lexicon` | extend the dictionaries (see above) |

One `Normalizer` can be shared by many threads: compiled state is built under a lock and swapped in
as one object, and lexicon edits are locked, so no thread sees half-built patterns.

## How it works

Text is split into spans. Code, URLs, e-mails, HTML and protected tokens are kept, math goes to the
LaTeX speaker, and the rest runs through these steps:

0. **Rule sets**, if given (their output is parked and restored at the end)
1. **Spelled tokens and abbreviations** (`H2O`, `Dr.` → "Doctor")
2. **Dates** and German ordinals (`15.03.2024`, `March 3rd`, `der 3. Platz`)
3. **Symbols that need digits** (`5 - 3`, `x^2`, `3 * 4`)
4. **Numbers**, with what follows: units, percent, currency, ordinals, am/pm
5. **Pauses and remaining symbols** (`—`, `=`, `+`, `²`, `≤`)

Regexes are compiled once and rebuilt only when the dictionaries change.

```
src/normt2s/
  normalizer.py    the pipeline above (start reading here)
  lexicon.py       the editable dictionaries and how they are loaded
  rules.py         Rule, RuleSet
  stream.py        buffering for streamed text, Piece
  markdown.py      Markdown marker stripping
  latex.py         LaTeX tokenizer, parser, speaker, bare-LaTeX detection
  langs/           per-language rules: number words, times, dates, fractions
  data/            en.json, de.json, elements.json: word lists and vocabulary
tests/             examples of every rule; tests/golden/ lists typical inputs and outputs
benchmarks/        bench.py
```

Rules that need code (how to build "twenty-one") live in `langs/`; word lists live in `data/`.

## Adding a language

1. Create `src/normt2s/langs/xx.py` with a subclass of `Language`: set the separators and words
   (`thousands_sep`, `decimal_sep`, `minus`, `point`, `percent`, ...) and implement `cardinal`,
   `ordinal`, `time` and `fraction`. Optionally add `year`, `decade`, `date_regex`/`format_date`,
   `ordinal_dot_regex`/`format_ordinal_dot`, `time_word`. End the file with
   `register(YourLanguage())`.
2. Import it in `langs/__init__.py`.
3. Create `src/normt2s/data/xx.json` in the format shown above.

`langs/en.py` and `langs/de.py` are working examples.

## Performance

`python benchmarks/bench.py` on a laptop (timings vary by about ±20% between runs):

| Input | Time |
|---|---|
| a typical sentence (74 characters) | about 55 µs |
| a 600-character paragraph | about 0.45 ms |
| a 700-character Markdown paragraph | about 0.36 ms |
| the sentence with a 200-rule `RuleSet` | about 63 µs |
| streaming 1,000 one-character chunks | about 8 ms |
| one-time startup | about 7 ms |

## Known limitations

- **Acronyms** such as "AI" or "LLM" are not expanded; add them with `add_abbreviation`.
- **`*` and ` / `** are only read between a digit, `)` or `]` and a digit, `(` or `[`; `·` also
  between single letters.
- **Subtraction:** `-` is only read as "minus" between two numbers with spaces (`5 - 3`), not in
  `x - 1`. In LaTeX math it is always read.
- **German ordinal dots** are recognised in dates and after an article or contraction before a
  capitalised word. The ending follows the article (`der`/`die`/`das` → *dritte*, else *dritten*),
  which is wrong for a feminine genitive or dative (`der 3. Klasse`). Without an article
  (`z. B. 3. Platz`) the ending would depend on the noun's gender, so it stays "drei. Platz".
- **German number + noun:** the gender is only known for nouns that are units in the lexicon
  (`1 Stunde`, `1 Kilogramm`); `1 Haus` stays "eins Haus". Teach nouns with `add_unit`.
- **Dates:** English `3/15/2024` and `15 March 2024`, and German two-digit years, are not handled.
- **Durations** such as `1:30:15` are not recognised.
- **Thousands:** a space between groups of three digits is a separator, so `3 100` is one number.
- **Single capital-letter units** (`V`, `W`, `L`, `N`, `J`) only match attached to the number
  (`12V`), so the J in `5 J` is not read as joules (`5 Ω` matches with a space). `A`, `K`, `C`, `F`
  and `T` exist only with a prefix (`mA`, `mK`, `µC`, `µF`, `mT`), so `Klasse 5A` is not five amperes
  and `4K` not four kelvin; their nouns still have a gender (`1 Kelvin` is "ein Kelvin").
- **LaTeX:** a lone `|` reads as "such that", so `P(A|B)` is not "given". Layout commands such as
  `\overset` and `\underbrace` are not interpreted.

## Development

```
pip install -e .[dev]
pytest
python benchmarks/bench.py
```

Before 1.0, a minor release may change spoken output and a patch release never does, so pin
`normt2s>=0.4,<0.5`. Every output change is listed in [CHANGELOG.md](CHANGELOG.md). The
hostile-input tests feed every entry point with 100 kB of repeated `*`, `_`, `{`, `$`, `\`, `` ` ``,
`[` and `::`. The tests double as documentation: see `tests/test_en.py` and `tests/test_de.py`.

## AI notice

This package was co-authored with Claude Code (Claude Sonnet 5.5, Anthropic). The code, tests and
documentation were written in collaboration between a human maintainer and the AI assistant.
Please review the output against your own requirements before relying on it in production.

## License

MIT, see [LICENSE](LICENSE).
