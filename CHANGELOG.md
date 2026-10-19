# Changelog

Before 1.0 a minor release may change spoken output; a patch release never does.

## Unreleased (0.2.0)

- Thread-safe compilation: `Normalizer` rebuilds its regexes under a lock and publishes them as
  one object, and `Lexicon` edits are locked. No change in output.
- **Bug fix (F1):** `add_symbol` now works for any symbol (`@`, `!=`, ...), not only a fixed set.
  An empty or whitespace key raises `ValueError`.
- **Output change (F1):** `3 * 4` -> "three times four", `3 / 4` (spaces) -> "three divided by four".
  New lexicon table `operators`.
- **Output change (F3):** `—` (em dash) is spoken as a pause (", "); `10—20` as a range. New
  lexicon table `punctuation` and `add_punctuation`.
