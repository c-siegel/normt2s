# normt2s

**Make written text speakable.** `normt2s` turns numbers, units, abbreviations, dates and math into
the words a text-to-speech engine should say, so `3.5 km/h` is not read as "three dot five k m
slash h".

- **English and German**
- **No dependencies**, pure Python 3.9+, MIT licensed
- **Fast**: about 90 µs for a typical sentence
- **Streaming-ready**: works on LLM output as it arrives, token by token
- **Easy to extend**: add words with one line of code or a small JSON file

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
4. [Math (LaTeX)](#math-latex)
5. [Streaming LLM output](#streaming-llm-output)
6. [Reference: options and API](#reference-options-and-api)
7. [How it works](#how-it-works)
8. [Adding a language](#adding-a-language)
9. [Performance](#performance)
10. [Known limitations](#known-limitations)
11. [Development](#development)

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

### What is left alone

Code (`` `inline` `` and fenced blocks), URLs, e-mail addresses, HTML tags and Markdown link
targets are never changed:

```python
normalize("Run `pip install numpy==1.26` and open https://example.com/v1.2/page")
# unchanged
```

Things that only look like numbers are kept too: versions with several dots are read digit by
digit (`3.2.1` is "three point two point one"), and letters glued to digits (`H2O`, `mp3`) are
not split.

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
| A math symbol such as `=` or `×` | `add_symbol(key, word)` | `("=", "is")` |
| A LaTeX command | `lexicon.add_latex_command(name, spoken)` | `("R", "the reals")` |
| A LaTeX function | `lexicon.add_latex_function(name, spoken)` | `("sinc", "sinc")` |
| A LaTeX sentence template | `lexicon.add_phrase(key, template)` | `("frac", "{a} divided by {b}")` |
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

## Reference: options and API

```python
Normalizer(lang="en", lexicon=None, latex="speak")
```

| Argument | Meaning |
|---|---|
| `lang` | `"en"` or `"de"` (or a `Language` object) |
| `lexicon` | a `Lexicon` to use instead of the built-in data |
| `latex` | `"speak"` (default) reads math aloud, `"keep"` leaves it untouched |

| Call | What it does |
|---|---|
| `normalize(text, lang="en")` | one-shot helper; `lang` may be a code or your own `Normalizer` |
| `get_normalizer(lang)` | the shared instance behind `normalize(text, "en")` |
| `n.normalize(text)` (or `n(text)`) | normalize a string |
| `n.stream(max_buffer=400)` | a `StreamNormalizer` with `feed()` and `flush()` |
| `n.normalize_stream(chunks)` | generator over speakable pieces |
| `n.add_*`, `n.load_lexicon(path)` | extend the dictionaries (see above) |
| `n.lexicon` | the underlying `Lexicon` with the LaTeX methods |

### Threads

One `Normalizer` can be shared by many threads (for example in a web server). Compiled state is
built under a lock and swapped in as a single object, and edits to the lexicon are locked, so a
thread never sees half-built patterns, even while another thread calls `add_abbreviation`.

## How it works

Text is split into spans. Code, URLs, e-mails and HTML are kept as they are, math goes to the
LaTeX speaker, and everything else runs through these steps:

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
  stream.py        buffering for streamed text
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
| a typical sentence (74 characters) | about 90 µs |
| a 600-character paragraph | about 0.9 ms |
| one-time startup (building and compiling) | about 30 ms |

## Known limitations

- **Acronyms** such as "AI" or "LLM" are not expanded by default. Add the ones you need with
  `add_abbreviation`.
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

The tests double as documentation: `tests/test_en.py` and `tests/test_de.py` list the expected
output for each rule.

## AI notice

This package was co-authored with Claude Code (Claude Sonnet 5.5, Anthropic). The code, tests and
documentation were written in collaboration between a human maintainer and the AI assistant.
Please review the output against your own requirements before relying on it in production.

## License

MIT, see [LICENSE](LICENSE).
