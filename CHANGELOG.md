# Changelog

Before 1.0 a minor release may change spoken output; a patch release never does.

## Unreleased

- **Output change:** isotopes are read with the element's name: `Co-60` -> "Kobalt sechzig" /
  "cobalt sixty" (was "C o sechzig"), `U-235` -> "Uran zweihundertfünfunddreißig". A metastable
  `m` is kept: `Tc-99m` -> "technetium ninety-nine m" (was "... ninety-nine meters"). New
  `"elements"` table and `Lexicon.add_element(symbol, name)`.

## 0.6.0

- **Output change:** SI-prefixed units are generated from their base units, with gender and plural
  from the base: `10 µF` -> "zehn Mikrofarad", `1013 hPa` -> "eintausenddreizehn Hektopascal", also
  `MΩ`, `MJ`, `mT`, `mSv`, `keV`, `TWh`, `µg`, `dl`, `mbar`, `mmol` and more. Each base takes only its
  common prefixes (no `Mm`, `cd`). Farad, Tesla, Ampere, Coulomb and Kelvin exist only with a
  prefix, so `5F` and `Klasse 5A` stay as they are. `μ` (Greek mu) works like `µ`.
- **New:** `add_prefixed_unit(base, prefixes, singular=None, plural=None, gender=None)`,
  `Lexicon.add_prefix(symbol, word)`, and `"prefixes"` / `"prefixed_units"` in lexicon files.
- **Output change:** new units `rad`, `Bq`, `Gy`, `Sv` (and English `t`, tonne). Kelvin, Ampere,
  Coulomb, Farad and Tesla exist only with a prefix, but their nouns take a gender: `1 Kelvin` ->
  "ein Kelvin". `5 Ω` is read with a space too ("five ohms"); other lone capitals still need `5V`.
- **Output change:** Greek letters and math signs in prose: `Δt` -> "Delta t", `λ`, `π`, `ℏ`, `∝`,
  `∞`, `→`, `⇒`, `⇔`, `√`, `‰`. Greek words stay as they are; `µ` before a unit stays a prefix.
- **Output change:** `½`, `¼`, `¾`: `1½ Stunden` -> "eineinhalb Stunden", `2¼` -> "two and a quarter".
  New `Language.mixed_fraction`.
- **Output change:** a symbol at the text's edge, inside brackets or before punctuation gets no
  extra space: `× 3` -> "mal drei" (was " mal drei"), `(×)` -> "(mal)".

## 0.5.0

- **Output change:** `·` between operands is multiplication: `F = m · a` -> "F gleich m mal a",
  `2·3` -> "two times three". Like `*` it lives in `operators`; `Lehrer·innen` and `Home · About` are
  untouched.
- **Output change:** `=` and `+` next to a rule's replacement are read: `F = 1 N` with a
  `{number} N` rule -> "F gleich ein Newton" (was "F = eins Newton").
- **Output change:** new units `N`, `kN`, `J`, `Wh`, `Ω`, `kΩ` and `mAh` (`N`, `kN`, `J`, `Wh` in
  English). German nouns take their gender: `1 Newton` -> "ein Newton" (was "eins Newton"). A
  single capital (`N`, `J`) only counts attached to the number (`10N`).
- **New:** `Rule(..., renormalize=True)` (`"renormalize": true` in JSON) reads a rule's replacement
  once more: `Rule("1 s", "1 Sekunde", renormalize=True)` -> "eine Sekunde".
- **Bug fix:** `add_protected` skips leading `^`, `\b` and lookarounds when it looks for the literal
  start, so `(?<![\w:])::[a-z_]+::(?![\w:])` works without `opener=`.

## 0.4.1

- **Output change (German):** a bare decimal comma in LaTeX is a decimal: `$1,23 \cdot x$` -> "eins
  Komma zwei drei mal x" (was "eins, dreiundzwanzig mal x"). Spaced lists (`1, 2`) and chains
  (`\{1,2,3\}`) stay lists; `(1,2)` now reads "eins Komma zwei" (write `(1;2)` for a pair).

## 0.4.0

- **Bug fix (German):** `um 14:30 Uhr` -> "um vierzehn Uhr dreißig" (was "... dreißig Uhr Uhr").
- **Output change:** a space, no-break space or thin space between groups of three digits is a
  thousands separator: `1 000 apples` -> "one thousand apples" (was "one zero zero zero").
- **Output change (F12, German):** `der 3. Platz` -> "der dritte Platz", `im 21. Jahrhundert` ->
  "im einundzwanzigsten Jahrhundert" (was "der drei. Platz"). New `Language.ordinal_dot_regex` hook.
- **Output change (F11, German):** a number before a known unit noun takes its gender: `1 Stunde` ->
  "eine Stunde" (was "eins Stunde"), `1 Kilogramm` -> "ein Kilogramm".
- **Bug fix (German):** a gender only shows on exactly 1: `101 h` -> "einhunderteins Stunden" (was
  "einhunderteine"), `1,5 kg` -> "eins Komma fünf Kilogramm" (was "ein Komma fünf").

## 0.3.0

- **New (F10):** `add_protected(pattern, spoken=None, opener=None)` and a `protected` list in lexicon files.
  Matches are kept, replaced or removed, and streams never cut inside them.
- **New (F9):** `Piece(raw, spoken)`, `stream.feed_pieces()` and `stream.flush_piece()`; `feed()` returns the
  joined `spoken` parts of everything released by one call; `normalize_stream` yields per piece.
- **New (F8):** `stream(first_min_chars=, min_chars=)` and the same on `normalize_stream`; the defaults keep
  the old behaviour. The `max_buffer` fallback no longer cuts inside a code, URL or math span, nor
  right after a year preposition (`in 1984`) or German date word (`am 15.03.`).

## 0.2.0

- Thread-safe compilation: `Normalizer` rebuilds its regexes under a lock and publishes them as
  one object, and `Lexicon` edits are locked. No change in output.
- **Bug fix (F1):** `add_symbol` now works for any symbol (`@`, `!=`, ...), not only a fixed set.
  An empty or whitespace key raises `ValueError`.
- **Output change (F1):** `3 * 4` -> "three times four", `3 / 4` (spaces) -> "three divided by four".
  New lexicon table `operators`.
- **Output change (F3):** `—` (em dash) is spoken as a pause (", "); `10—20` as a range. New
  lexicon table `punctuation` and `add_punctuation`.
- **Bug fix (F5):** bare LaTeX outside math delimiters is no longer rewritten by the number pass
  (`\frac{1}{2}` stays). New option `latex_bare="speak"` reads it aloud.
- **Output change (F4):** built-in formulas are spelled (`H2O` -> "H two O"), isotopes `U-235` ->
  "U two hundred thirty-five". New lexicon list `spelled`, `add_spelled`, `data/elements.json`.
- **New (F2):** `markdown="strip"` removes Markdown markers (off by default). Streams hold back
  unclosed markers. The e-mail pattern no longer takes quadratic time on long runs of `_`.
- **New (F6):** `Rule` and `RuleSet`: literal pronunciation rules with a `{number}` placeholder that
  run inside the pipeline (`normalize(text, rules=..., applied=...)`, `stream(rules=...)`).
  `Lexicon.unit_nouns` is a new reverse index of unit words.
