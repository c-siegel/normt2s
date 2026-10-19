# Changelog

Before 1.0 a minor release may change spoken output; a patch release never does.

## 0.4.0

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
