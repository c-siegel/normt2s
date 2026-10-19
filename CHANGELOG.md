# Changelog

Before 1.0 a minor release may change spoken output; a patch release never does.

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
