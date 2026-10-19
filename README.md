# normt2s

**Make written text speakable.** `normt2s` turns numbers, units, abbreviations, dates and math into
the words a text-to-speech engine should say, so `3.5 km/h` is not read as "three dot five k m
slash h".

- **English and German**
- **No dependencies**, pure Python 3.9+, MIT licensed
- **Fast**: about 100 µs for a typical sentence
- **Streaming-ready**: works on LLM output as it arrives, token by token
- **Easy to extend**: add words with one line of code or a small JSON file, or let users bring their own pronunciation rules
- **LLM-ready**: optional Markdown stripping, bare LaTeX and chemical formulas

```python
from normt2s import normalize

normalize("It costs $3.50 for 2 kg, e.g. in 1984.")
# 'It costs three dollars and fifty cents for two kilograms, for example in nineteen eighty-four.'

normalize("Der Zug fährt 120 km/h, z. B. um 14:30.", lang="de")
# 'Der Zug fährt einhundertzwanzig Kilometer pro Stunde, zum Beispiel um vierzehn Uhr dreißig.'
```

## Contents

1. [Install](#install)
2. [What gets converted](#what-gets-converted)
3. [Adding your own words](#adding-your-own-words)
4. [Markdown](#markdown)
5. [Rule sets for pronunciations](#rule-sets-for-pronunciations)
6. [Math (LaTeX)](#math-latex)
7. [Streaming LLM output](#streaming-llm-output)
8. [Reference: options and API](#reference-options-and-api)
9. [How it works](#how-it-works)
10. [Adding a language](#adding-a-language)
11. [Performance](#performance)
12. [Known limitations](#known-limitations)
13. [Development](#development)

## Install

`normt2s` is available on [PyPI](https://pypi.org/project/normt2s/):

```
pip install normt2s
```

To work on the library itself, install from a clone of the repository instead:

```
pip install -e .
```

## What gets converted

Every row is real output from the library.

### English

| Category | Input | Spoken |
|---|---|---|
| Numbers | `1,234 points` | one thousand two hundred thirty-four points |
| | `3.14`, `-5`, `007` | three point one four, minus five, zero zero seven |
| | `1st`, `23rd` | first, twenty-third |
| | `50%`, `1/2 cup` | fifty percent, one half cup |
| Years | `in 1984`, `the 1990s` | in nineteen eighty-four, the nineteen nineties |
| | `I have 1984 apples` | I have one thousand nine hundred eighty-four apples |
| Time | `3:45 pm`, `at 14:30` | three forty-five p m, at fourteen thirty |
| Dates | `March 3rd, 2024`, `2024-03-15` | March third, twenty twenty-four; March fifteenth, twenty twenty-four |
| Units | `100 km/h`, `20°C`, `9.81 m/s²`, `1 ft` / `2 ft` | one hundred kilometers per hour, twenty degrees Celsius, nine point eight one meters per second squared, one foot / two feet |
| Currency | `$3.50`, `€5`, `5 EUR`, `$2.5 million` | three dollars and fifty cents, five euros, five euros, two point five million dollars |
| Abbreviations | `Dr. Smith, e.g. ...`, `etc.` | Doctor Smith, for example ..., et cetera |
| Math symbols | `2 + 3 = 5`, `x²`, `a ≤ b` | two plus three equals five, x squared, a is less than or equal to b |
| Chemistry | `H2O`, `CO2`, `U-235` | H two O, C O two, U two hundred thirty-five |
| Pauses | `The result — a success — was clear.` | The result, a success, was clear. |
| Operators | `3 * 4 * 5`, `2*(x+1)`, `3 / 4` | three times four times five, two times (x plus one), three divided by four |

### German

| Category | Input | Spoken |
|---|---|---|
| Numbers | `1.234,5` | eintausendzweihundertvierunddreißig Komma fünf |
| | `1/3`, `3/4` | ein drittel, drei viertel |
| Dates | `15.03.2024` | fünfzehnter März zweitausendvierundzwanzig |
| | `am 15.03.2024` | am fünfzehnten März zweitausendvierundzwanzig |
| | `am 3. Mai`, `im Mai 2024` | am dritten Mai, im Mai zweitausendvierundzwanzig |
| Time | `um 14:30` | um vierzehn Uhr dreißig |
| Units | `1 kg`, `1 min`, `21 min` | ein Kilogramm, eine Minute, einundzwanzig Minuten |
| Currency | `3,50 €`, `5 €` | drei Euro fünfzig Cent, fünf Euro |
| Abbreviations | `z. B.`, `ca. 5 Mio.` | zum Beispiel, circa fünf Millionen |

German dates take the right case ending from the word before them: `am` / `vom` / `zum` / `dem`
/ `den` give *fünfzehnten*, `der` gives *fünfzehnte*, and a date on its own gives *fünfzehnter*.

### Symbols and operators

`add_symbol` accepts any single character or character sequence without whitespace (an empty or
whitespace key raises `ValueError`): `n.add_symbol("@", "at")` reads `5 @ 3` as "five at three".

`*` and `/` are ambiguous in prose, so they have their own built-in `operators` table and are only
read between operands: `3 * 4 * 5`, `3*4*5` and `2*(x+1)` use "times"; `3 / 4` (spaces required)
uses "divided by". `1/2` stays a fraction, and `a * b`, `*word*`, `**bold**` and `and/or` are not
touched. In a lexicon file, use an `"operators": {"*": "times", "/": "divided by"}` table.

### Spelled tokens

A TTS engine reads `CO2` as one made-up word, so a list of chemical formulas is spelled out:
letters as themselves, digit runs as numbers (`H2O` is "H two O", `C6H12O6` is "C six H twelve
O six"). `CO_2` matches too. Built in: `CO2 H2O O2 O3 N2 H2 CH4 NH3 NaCl H2SO4 HCl NaOH CaCO3 SO2 NO2
C6H12O6`. Add more with `n.add_spelled("ATP5")` or a `"spelled": [...]` list in a lexicon file.
Matching is whole-token: `ECO2000` and `CO23` are left alone.

Isotopes written `U-235` (an element symbol, hyphen, one to three digits) are read without the
hyphen: "U two hundred thirty-five". `A-4` (not an element) is not touched by this rule.

### Pauses

Many TTS engines read an em dash (`—`) as "minus". By default it becomes a comma pause, and between
two digits it is a range like the en dash: `10—20` is "ten to twenty". A dash at the start or end of
a line is dropped, and no doubled commas are produced. Change or extend it with
`n.add_punctuation("…", " dot dot dot ")` or a `"punctuation"` table in a lexicon file.

### What is left alone

Code (`` `inline` `` and fenced blocks), URLs, e-mail addresses, HTML tags and Markdown link
targets are never changed:

```python
normalize("Run `pip install numpy==1.26` and open https://example.com/v1.2/page")
# unchanged
```

Things that only look like numbers are kept too: versions with several dots are read digit by
digit (`3.2.1` is "three point two point one"), and letters glued to digits (`mp3`, `ECO2000`) are
not split. Listed formulas such as `H2O` are the exception, see *Spelled tokens*.

## Adding your own words

There is one rule to remember: **create a `Normalizer`, add words to it, and use that instance.**

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

> **Gotcha:** `normalize(text, "en")` uses a separate, shared instance. Words you add to your own
> `Normalizer("en")` are **not** visible there. Pass your instance (`normalize(text, n)`), or edit
> the shared one with `get_normalizer("en")`.

Your entries override the built-in ones, and changes apply immediately, even to an instance you
have already used.

### Which method for what

| You want to change | Method | Example |
|---|---|---|
| An abbreviation | `add_abbreviation(key, to)` | `("tbh", "to be honest")` |
| A unit after a number | `add_unit(symbol, singular, plural, gender)` | `("kn", "knot")` |
| A currency | `add_currency(symbol, major, minor)` | see above |
| A math symbol such as `=` or `×`, or any other character or sequence | `add_symbol(key, word)` | `("=", "is")`, `("@", "at")`, `("!=", "is not")` |
| `*` or ` / ` between operands | `lexicon.add_operator(key, word)` | `("*", "times")` |
| A LaTeX command | `lexicon.add_latex_command(name, spoken)` | `("R", "the reals")` |
| A LaTeX function | `lexicon.add_latex_function(name, spoken)` | `("sinc", "sinc")` |
| A LaTeX sentence template | `lexicon.add_phrase(key, template)` | `("frac", "{a} divided by {b}")` |
| A token spelled out letter by letter | `add_spelled(token)` | `("ATP5")` |
| A character read as a pause | `add_punctuation(char, replacement)` | `("—", ", ")` |
| Remove an entry | `lexicon.remove(kind, key)` | `("abbreviations", "vs.")` |

Notes on abbreviations:

- Matching is case sensitive, but for lowercase keys a capitalised variant is added for you
  (`e.g.` also gives `E.g.` → "For example"). Pass `capitalized=False` to turn that off.
- Spaces inside a key are optional when matching: `z. B.` also matches `z.B.`
- Set `final=True` for abbreviations that can end a sentence (`etc.`), so the full stop is kept
  when a new sentence follows.

### Using a file

Put your words in a JSON (or, on Python 3.11+, TOML) file and load it:

```python
n.load_lexicon("my_terms.json")
```

```json
{
  "abbreviations": {
    "LMS": "learning management system",
    "etc.": {"to": "et cetera", "final": true}
  },
  "units": {"kn": ["knot"], "ch": ["child", "children"]},
  "currencies": {"CHF": {"major": ["franc", "francs"], "minor": ["rappen", "rappen"]}},
  "symbols": {"=": "equals"},
  "latex": {
    "commands": {"R": "the reals"},
    "functions": {"sinc": "sinc"},
    "phrases": {"frac": "{a} divided by {b}"}
  }
}
```

The built-in data uses exactly this format: see [src/normt2s/data/en.json](src/normt2s/data/en.json)
and [de.json](src/normt2s/data/de.json). A unit entry is `[singular, plural, gender]`, where the
plural and gender are optional and the gender (`"m"`, `"f"`, `"n"`) only matters in German.

## Markdown

LLM replies are usually Markdown, and read aloud `**`, `#` or `[text](url)` are noise. Opt in with
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
| Inline code | `` `x = 1` `` | `x = 1`, kept verbatim |
| Fenced code | ```` ```python\ncode\n``` ```` | `code`, kept verbatim, the language label is dropped |

Code, URLs, e-mail addresses, HTML and math are masked before the markers are removed, so
`snake_case_name`, `` `a*b*c` `` and `$a_1 * b_1$` are safe, and `3*4*5` is not mistaken for
emphasis. In a stream, an unclosed `**`, `__`, `~~`, `*x`, `_x` or `[text](` is held back until
it is closed or the line ends, and a cut never falls inside a complete emphasis or link.

Not handled: tables, footnotes and reference-style links (`[text][ref]`). A line starting with a
number and a dot (`3. Mai war schön`) is a list item in Markdown and loses the number.

## Rule sets for pronunciations

Applications often let users fix pronunciations: `pH` should be "p H", `{number} kg` should be
"{number} kilograms". Replacing before the normalizer breaks grammar (German `1 Kilogramm` would be
"eins Kilogramm"), and replacing after it misses because numbers are already words. A `RuleSet`
runs inside the pipeline instead:

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

`Rule(term, spoken, whole_word=True, case_sensitive=False, gender=None, plural=None)` is a frozen
dataclass. A `RuleSet` is immutable and hashable by content, so you can cache one per user with
`functools.lru_cache`. One shared `Normalizer` per language serves any number of rule sets, and a
rule set never changes the lexicon. `n.stream(rules=...)` and `n.normalize_stream(chunks,
rules=...)` take it too, and `normalize(text, "en", rules)` as well.

Load rules from data:

```python
RuleSet.from_dicts([{"term": "pH", "spoken": "p H", "case_sensitive": True}])
RuleSet.load("rules.json")      # {"rules": [ ...same dictionaries... ]}
```

`from_dicts` also accepts the camelCase keys `caseSensitive` and `wholeWord`, which JavaScript
front ends usually send.

How terms match:

- A term is **literal text**, no regular expressions. A space matches any run of whitespace, so
  `e. g.` also matches across a line break.
- `{number}` matches `5`, `1,5`, `3.000,25` or `1,234.5` (a leading minus is included) and may be
  used several times; `{number}` in `spoken` is replaced in order by the number in words.
- `whole_word=True` keeps a rule from matching inside a word: `N` does not match in `Newton`, but
  `kg` matches in `10kg`. Terms that start or end with a symbol (`°C`, `≈`) need no guard.
- The longest term wins, then plain terms before templates, then case-sensitive before
  case-insensitive. Text is scanned once from left to right and a replacement is never matched
  again. A replacement that would touch a neighbouring letter or digit is padded with a space
  (`Δt` is "Delta t").
- After `{number}`, the spoken word is looked up among the units: its gender is used for the
  number (German `1 kg` is "ein Kilogramm") and singular or plural is chosen from the value
  (`21 min` becomes "einundzwanzig Minuten"). `gender=` and `plural=` override this.
- Empty terms are ignored. Terms longer than 200 characters and sets of more than 2,000 rules
  raise `ValueError`.

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

Supported: fractions, roots, powers and subscripts, sums, products, integrals and limits, Greek
letters, relations and set notation, functions such as `\sin` and `\log`, absolute values and
norms, accents (`\vec`, `\hat`), `\binom`, factorials, primes, matrices, `cases`, and `\text{}` /
`\mathrm{}`. Units after a number work too: `5\,\mathrm{km}` is "five kilometers".

Good to know:

- **Parentheses** are only spoken where they change the meaning: `(a+b)^2` and `2(x+1)` get
  "open paren ... close paren", `y = (x+1)` does not.
- **Complex arguments** are fenced so the listener can follow them: "the square root of x plus
  one, end root".
- **Malformed LaTeX** never raises. It is left exactly as it was written.
- **Dollar signs:** a single `$` only starts math under the pandoc rule, so
  `from $5 to $6` stays currency.
- **Bare LaTeX** (without `$...$`) such as `\frac{1}{2}` or `a \cdot b` is protected by default:
  its numbers are not rewritten (before, `\frac{1}{2}` became `\frac{one}{two}`). Use
  `Normalizer("en", latex_bare="speak")` to read it like delimited math. A run starts at a known
  command and stops before a word, a sentence mark or a newline; unknown commands
  (`C:\Users\name`) and unbalanced braces are left as they are.
- **Turn it off** with `Normalizer("en", latex="keep")` to leave all math untouched.
- **Commands vs. functions:** `add_latex_command` is for symbol-like names (`\cdot`, `\R`),
  `add_latex_function` for names applied to an argument (`\sinc x`). Commands win when both exist,
  and `add_latex_function` warns if a command with that name already exists.

## Streaming LLM output

When the LLM answers token by token, you do not want to wait for the full answer, and you cannot
normalize each token alone (`"1"`, `"20"`, `" km"` would be read separately). The stream wrapper
buffers text and releases it only when it is safe:

```python
stream = n.stream()
for token in llm_tokens:
    speakable = stream.feed(token)     # "" until a safe boundary is reached
    if speakable:
        tts.say(speakable)
tts.say(stream.flush())                # call once at the end
```

or, as a generator:

```python
for speakable in n.normalize_stream(llm_tokens):
    tts.say(speakable)
```

What that looks like:

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

Text is released at the end of a sentence or at a newline. It is never cut inside a number and its
unit, an abbreviation (`Dr. Smith`), a date (`am 3. Mai`), a code block or a math span. The
combined output is identical to normalizing the whole text at once, whatever the chunk sizes (this
is tested). If a long run has no boundary, it is flushed after `max_buffer` characters (default
400) at a whitespace that does not follow a number.

The trade-off: speech starts at the end of the first sentence, not at the first token.

### Chunk sizes

A voice UI wants the first audio early and later chunks long enough to sound natural and to save
TTS requests:

```python
stream = n.stream(first_min_chars=25, min_chars=80, max_buffer=300)
```

- Before anything has been released, the **first** boundary at least `first_min_chars` long is
  used, so the first chunk is short.
- After that, text is released at the **last** boundary, but only once that is at least
  `min_chars` long; otherwise the stream waits.
- `max_buffer` is the fallback for a long run without a boundary, as before. It never cuts right
  after a word that gives the next number its meaning (`in 1984`, German `am 15.03.`).
- `flush()` releases everything, however short.
- The defaults (`0`, `0`) keep the old behaviour. Whatever the three values, the joined output
  is identical to normalizing the whole text at once (tested with random texts and chunkings).

One `feed()` call releases at most one chunk, so with `first_min_chars` the rest of a very large
token is released by the next `feed()` or by `flush()`.

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
| `markdown` | `"keep"` (default) or `"strip"` to remove Markdown markers before normalizing |

| Call | What it does |
|---|---|
| `normalize(text, lang="en")` | one-shot helper; `lang` may be a code or your own `Normalizer` |
| `get_normalizer(lang)` | the shared instance behind `normalize(text, "en")` |
| `n.normalize(text, rules=None, applied=None)` (or `n(text)`) | normalize a string, optionally with a `RuleSet` |
| `n.stream(max_buffer=400, first_min_chars=0, min_chars=0, rules=None)` | a `StreamNormalizer` with `feed()` and `flush()` |
| `n.normalize_stream(chunks, max_buffer=400, first_min_chars=0, min_chars=0, rules=None)` | generator over speakable pieces |
| `Rule(...)`, `RuleSet(rules)`, `RuleSet.from_dicts(...)`, `RuleSet.load(path)` | user pronunciation rules (see above) |
| `n.add_*`, `n.load_lexicon(path)` | extend the dictionaries (see above) |
| `n.lexicon` | the underlying `Lexicon` with the LaTeX methods |

### Threads

One `Normalizer` can be shared by many threads (for example in a web server). Compiled state is
built under a lock and swapped in as a single object, and edits to the lexicon are locked, so a
thread never sees half-built patterns, even while another thread calls `add_abbreviation`.

## How it works

Text is split into spans. Code, URLs, e-mails and HTML are kept as they are, math goes to the
LaTeX speaker, and everything else runs through these steps:

0. **Rule sets**, if given (their output is parked and restored at the end)
1. **Abbreviations** (`Dr.` → "Doctor")
2. **Dates** (`15.03.2024`, `March 3rd`)
3. **Symbols that need digits** (`5 - 3`, `x^2`)
4. **Numbers**, together with what follows them: units, percent, currency, ordinals, am/pm
5. **Remaining symbols** (`=`, `+`, `²`, `≤`)

All regular expressions are compiled once and rebuilt only when the dictionaries change.

```
src/normt2s/
  __init__.py      public API: normalize, get_normalizer
  normalizer.py    the pipeline above (start reading here)
  lexicon.py       the editable dictionaries and how they are loaded
  rules.py         user rule sets (Rule, RuleSet)
  stream.py        buffering for streamed text
  markdown.py      Markdown marker stripping
  latex.py         LaTeX tokenizer, parser and speaker
  langs/           per-language rules: number words, times, dates, fractions
  data/            en.json, de.json: abbreviations, units, currencies, symbols, math vocabulary
tests/             examples of every rule, a good way to see expected behaviour
benchmarks/        bench.py
```

Rules that need code (how to build "twenty-one") live in `langs/`. Everything that is just a word
list lives in `data/`.

## Adding a language

1. Create `src/normt2s/langs/xx.py` with a subclass of `Language`: set the separators and words
   (`thousands_sep`, `decimal_sep`, `minus`, `point`, `percent`, ...) and implement `cardinal`,
   `ordinal`, `time` and `fraction`. Optionally add `year`, `decade`, `date_regex` and
   `format_date`. End the file with `register(YourLanguage())`.
2. Import it in `langs/__init__.py`.
3. Create `src/normt2s/data/xx.json` in the format shown above.

`langs/en.py` and `langs/de.py` are working examples.

## Performance

`python benchmarks/bench.py` on a laptop:

| Input | Time |
|---|---|
| a typical sentence (74 characters) | about 100 µs |
| a 600-character paragraph | about 0.85 ms |
| a 700-character Markdown paragraph (`markdown="strip"`) | about 0.7 ms |
| the sentence with a 200-rule `RuleSet` | about 130 µs |
| streaming 1,000 one-character chunks | about 13 ms |
| one-time startup (building and compiling) | about 25 ms |

## Known limitations

- **Acronyms** such as "AI" or "LLM" are not expanded by default. Add the ones you need with
  `add_abbreviation`.
- **Multiplication and division:** `*` and ` / ` are only read between a digit, `)` or `]` and
  a digit, `(` or `[` (`a * b` is left alone).
- **Subtraction:** `-` is only read as "minus" between two numbers with spaces around it
  (`5 - 3`). In `x - 1` it is left as it is. In LaTeX math it is always read.
- **German ordinal dots** are only recognised in dates (`am 3. Mai`), not in general
  (`der 3. Platz`).
- **German number + noun:** `1 Stunde` reads "eins Stunde", because the gender of a spelled-out
  noun is unknown. Use the unit symbol (`1 h`) to get "eine Stunde".
- **Dates:** English `3/15/2024` and `15 March 2024` are not handled, and neither are German
  two-digit years.
- **Durations** such as `1:30:15` are not recognised.
- **Single capital-letter units** (`V`, `W`, `L`) only match when attached to the number (`12V`),
  so that "5 A grade" is not read as five amperes.
- **LaTeX:** a lone `|` reads as "such that", so `P(A|B)` is not "given". Layout commands such as
  `\overset` and `\underbrace` are not interpreted.

## Development

```
pip install -e .[dev]
pytest
python benchmarks/bench.py
```

Before 1.0, a minor release may change spoken output and a patch release never does, so pin
`normt2s>=0.2,<0.3`. Every change of output is listed in [CHANGELOG.md](CHANGELOG.md); the golden
files in `tests/golden/` list typical inputs and their output per language.
The hostile-input tests feed every entry point with 100 kB of repeated `*`, `_`, `{`, `$`, `\`,
`` ` ``, `[` and `::`.

The tests double as documentation: `tests/test_en.py` and `tests/test_de.py` list the expected
output for each rule.

## AI notice

This package was co-authored with Claude Code (Claude Sonnet 5.5, Anthropic). The code, tests and
documentation were written in collaboration between a human maintainer and the AI assistant.
Please review the output against your own requirements before relying on it in production.

## License

MIT, see [LICENSE](LICENSE).
