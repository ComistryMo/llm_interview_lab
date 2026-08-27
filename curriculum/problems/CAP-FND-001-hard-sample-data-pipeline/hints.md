# Hints

## H1 — contract

Separate strict record validation from aggregation. Decide what must be known
before the destination can safely be replaced.

## H2 — structure

Accumulate validated records and counters, derive defensive hard-sample copies,
write only after validation succeeds, then slice new batch lists.

## H3 — debugging

Check exact container types, `type(value) is int`, line numbers, the threshold
comparison, compact UTF-8 JSONL, last-batch handling, and nested list aliases.
