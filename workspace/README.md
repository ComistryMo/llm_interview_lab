# Local Workspace

`workspace/` is the repository-local home for learner profiles. Clone this
repository once, then create a private profile with:

```bash
llm-lab init --profile default
```

Tracked public assets are limited to the schemas, the default template, the
fully fictional demo, and `profiles/.gitkeep`. Everything below
`workspace/profiles/` is ignored by Git. Do not force-add real profiles.

Each local profile contains `profile.yaml`, an append-only `events.jsonl`, and
the directories `submissions/`, `generated/`, `private_tests/`, `reviews/`,
`cache/`, and `exports/`.

The event file is the learning-history source of truth. Its physical line
order is reducer order; timestamps are evidence and are never used to reorder
events. The first version supports one writer process at a time.

The `demo/` profile is invented for tests. It is not derived from a real
learner or maintainer record. CI must not inspect `profiles/`.
