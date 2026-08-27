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
the directories `materials/`, `submissions/`, `generated/`, `private_tests/`,
`reviews/`, `interviews/`, `cache/`, and `exports/`. Structured `career_intent`
lives in `profile.yaml`; registered material metadata and SHA-256 values live
in `materials/manifest.json`.

The event file is the learning-history source of truth. Its physical line
order is reducer order; timestamps are evidence and are never used to reorder
events. Practice mistake summaries are derived from this history rather than
stored in another file. The verified retention schedule is D+2 and D+7; there
is no D+5 gate. The first version supports one writer process at a time.

Materials are copied only after an explicit `llm-lab material add`. AI access
requires an AI-eligible text file, an explicit material ID, per-interview
consent, and a matching SHA-256. A sanitized real interview question uses kind
`interview_question`; it remains private and never becomes a public Catalog
problem automatically.

For bring-your-own AI workflows, use `llm-lab context` and treat its
`read_allowlist` as exhaustive. The project has no built-in model client and
does not scan Profiles, upload files, or grant mastery through AI output.

The `demo/` profile is invented for tests. It is not derived from a real
learner or maintainer record. CI must not inspect `profiles/`.
