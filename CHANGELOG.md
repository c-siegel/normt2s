# Changelog

Before 1.0 a minor release may change spoken output; a patch release never does.

## Unreleased (0.2.0)

- Thread-safe compilation: `Normalizer` rebuilds its regexes under a lock and publishes them as
  one object, and `Lexicon` edits are locked. No change in output.
