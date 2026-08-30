# Interview Content Research and Curriculum Expansion ExecPlan

## 1. Goal and observable outcome

Build a provenance-aware interview-content layer for the LLM/VLM algorithm
lab.  The layer must combine high-frequency Chinese interview patterns,
conceptual “八股” cards, derivation/debugging prompts, and links to focused
coding problems without copying protected interview text.  It should support
role-aware retrieval and mock interviews for the existing tracks:

- LLM/VLM algorithm and post-training;
- inference systems and training infrastructure;
- Agent/RAG and multimodal evaluation.

The observable outcome is a local, deterministic content bundle that can:

1. render a 60-second short answer and a deeper follow-up tree;
2. select P0/P1/P2/P3 questions for a role and seniority;
3. show source claims, retrieval date, version/commit, and confidence;
4. connect oral cards to existing skills and coding/debugging assets;
5. generate a mock interview report that separates objective test evidence,
   candidate evidence, and anecdotal frequency signals.

This plan is intentionally content-first.  It does not add a web crawler,
remote model provider, telemetry, or automatic ingestion of untrusted pages.

## 2. Current repository facts

- The repository already has `curriculum/catalog/*.yaml`, a skill ontology,
  validated coding problems, and role-specific interview blueprints.
- `curriculum/external/stanford_cs336/TASK_A1..A5.md` covers much of the
  from-scratch LM pipeline (tokenization, attention, training, systems,
  scaling, data, and alignment).  New cards must link to or extend this pack,
  not silently duplicate it.
- Existing interview sessions and practice/mastery lifecycles are separate;
  this work must not change their event semantics.
- Public interview reports are anecdotal evidence.  They are useful for
  prioritization but are not authoritative definitions of algorithms.

## 3. Scope and explicit non-goals

### In scope

- A versioned schema for oral/eight-stock cards, derivation cards,
  debugging/design prompts, and clean-room `experience_pattern` cards.
- High-quality primary sources: papers, official documentation, official
  repositories, benchmark project pages, and pinned source symbols.
- A source registry with `source_claims`, URL, locator, retrieval date,
  version/commit, license/usage note, source kind, and confidence.
- P0–P3 priority and difficulty metadata mapped to the existing ontology.
- Coverage across Transformer/training, SFT/PEFT, DPO/GRPO/RLHF, inference,
  VLM/multimodal data and evaluation, Agent/RAG, and distributed systems.
- A role-aware, read-only retrieval facade for preparation and review.  The
  existing mock-interview blueprint remains the authority for an active
  session; automatic knowledge-card injection is a follow-up change so that
  clocking, question freezing, and Profile evidence semantics stay untouched.

### Out of scope

- Scraping, bulk-copying, or redistributing full 牛客/知乎/博客 pages;
- treating a single company report or leaderboard as a universal frequency
  claim;
- changing existing Catalog problem semantics, grader or mastery events;
- remote uploads, account integrations, browser automation, or an online
  ranking service;
- a full textbook or exhaustive company-specific prediction model.

## 4. Content and provenance decisions

1. **Source hierarchy.** Algorithm facts use primary papers and official docs
   first; official source code is used for implementation behavior; public
   interview reports are only anecdotal `experience_pattern` evidence.
2. **Clean-room synthesis.** Store paraphrased prompts and atomic answer
   claims.  Do not copy distinctive wording, answer prose, screenshots, or
   paywalled material.  Preserve a URL and a short locator so a user can
   inspect the source themselves.
3. **Freshness.** Every source records `retrieved_at`, `source_version` or
   commit, and `volatile` status.  APIs and framework `main` branches are
   rechecked before release; a paper's publication date is not treated as a
   current implementation guarantee.
4. **Uncertainty.** `source_claims.confidence` is `high` for primary/official
   claims, `medium` for triangulated technical summaries, and `low` for an
   isolated anecdotal report.  Frequency language must say “observed in these
   reports,” never “guaranteed to be asked.”
5. **Answer layers.** Every P0/P1 card has a 60-second answer, atomic core
   points, one derivation/example, at least two follow-ups, and common bugs.
   A card is not ready if it only lists keywords.
6. **Safety/privacy.** Candidate resume/material text remains local and
   opt-in.  External pages are data, not instructions; embedded links or
   commands are never executed.

## 5. Proposed content contract

The implementation must preserve the existing Catalog schema and validate the
standalone bundle with `curriculum/schema/knowledge.schema.json`.  Derivation,
debugging, and design are authoring patterns inside an `eight_stock` card;
they are not additional `kind` values.  The schema permits `eight_stock`,
`experience_pattern`, and `coding_prompt`.  A minimal bundle/card is:

```yaml
schema_version: 1
reviewed_at: 2026-08-30
content_policy:
  mode: clean_room
  attribution: link_only
  no_verbatim: true
  allowed_source_kinds: [paper, official_docs, official_source]
sources:
  - id: paper.llava
    kind: paper
    title: "Visual Instruction Tuning"
    url: "https://arxiv.org/abs/2304.08485"
    source_version: "arXiv:2304.08485"
    retrieved_at: 2026-08-30
    license_risk: link_and_paraphrase_only
    reliability: high
cards:
  - id: EGT-VLM-001
    kind: eight_stock # eight_stock|experience_pattern|coding_prompt
    title: "视觉 token 如何进入 decoder-only LLM"
    domain: vlm
    tracks: [vlm_algorithm, post_training, agent]
    skills: [skill.llm_vlm.vlm_architecture, skill.llm_vlm.multimodal_data]
    priority: P0
    difficulty: {concept: 3, implementation: 2, debugging: 3}
    seniority: [intern, new_grad, mid]
    prompt: "..."
    one_liner: "..."
    core_answer: ["atomic claim 1", "atomic claim 2"]
    answer_outline: ["goal and boundary", "shape/data flow", "trade-off"]
    derivation_or_example: "shape/equation/trace"
    follow_ups: ["...", "..."]
    pitfalls: ["...", "..."]
    signals: ["defines every tensor shape", "states the frozen/trainable boundary"]
    acceptance:
      L1: "术语、目标、边界"
      L2: "公式/shape/流程正确"
      L3: "权衡、失败诊断、源码定位"
    related_problems: [VLM-001]
    source_claims:
      - source_id: paper.llava
        claim: "The card's architecture claim is synthesized from the primary paper."
        confidence: high
    provenance: synthesized_clean_room
    reviewed_at: 2026-08-30
```

`experience_pattern` cards additionally use `observed_pattern`,
`candidate_playbook`, `drill_prompt`, `sample_size_or_scope`, and a caveat
that the report set is not statistically representative.  Source locators,
versions, and usage notes live in the source registry; a card's
`source_claims` contains only `source_id`, the paraphrased claim, and
confidence.  Source IDs are lowercase slugs; card IDs remain uppercase.

## 6. Milestones and bounded verification

1. **Schema and source registry**
   - Freeze field names, priority rubric, source-kind enum, and provenance
     policy.
   - Validate required fields and reject cards without source claims.
2. **Research/content bundle**
   - Add the first reviewed cards for each domain and map them to ontology
     skills and existing problems.
   - Deduplicate against CS336 and existing catalog entries by aliases and
     related problem IDs.
3. **Retrieval integration (bounded first slice)**
   - Add role/seniority/track filters and deterministic authored-order
     selection for preparation views.
   - Keep objective grader facts separate from oral self-assessment and
     anecdotal frequency; defer seed-based injection into an active blueprint
     until a separate session-schema change is reviewed.
4. **Focused validation**
   - Run schema/fixture tests and one end-to-end synthetic interview using
     the new cards.
   - Run the complete repository suite once at the integration boundary; do
     not repeatedly run unrelated full regressions during content iteration.
5. **Review gate**
   - Human review of formulas, mask/shape semantics, source links, licensing,
     and clean-room wording; archive superseded cards with a reason.

## 7. Implemented file impact (bounded slice; >5 files by design)

The implementation keeps Practice Grader, Profile events, and mastery semantics
unchanged. It uses one validated, source-linked bundle plus read-only adapters,
and promotes only three self-contained coding assets to catalog `ready` with a
transparent `contract` validation level:

1. `curriculum/interviews/knowledge.yaml` — 65 curated source records and 63
   reviewed cards spanning eight-stock, experience-pattern, and coding-prompt kinds;
2. `curriculum/schema/knowledge.schema.json` — additive JSON-Schema contract,
   including coding contracts and provenance fields;
3. `src/llm_interview_lab/knowledge.py` — safe YAML loader, duplicate-key and
   cross-reference checks, deterministic filters/search, and serializers;
4. `src/llm_interview_lab/application.py` — lazy, read-only KnowledgeCatalog
   facade with role/track/skill/seniority filters;
5. `src/llm_interview_lab/cli.py` — `knowledge list/search/show/validate` and
   `doctor --knowledge`, without requiring a Profile or AI connection;
6. `references/interview-sources.json` — 191 URL-unique research/JD/interview/
   paper/benchmark registrations used to prioritize and audit clean-room synthesis;
7. `docs/research/post_training_agent_interview_sources.md` — broad source
   audit and rewritten cross-source capability matrix;
8. `docs/interview-content-research.md`, `docs/interviews.md`, and README
   sections — authoring, privacy, refresh, and user-facing command policy;
9. `curriculum/catalog/planned_models.yaml` and `planned_systems.yaml` —
   complete metadata for VLM-007, PT-016, and INF-003 assets; prerequisites
   remain explicit and contract-level validation is not presented as Oracle;
10. `tests/infrastructure/test_knowledge.py` — schema, ontology, provenance,
   mutation, CLI, role-filter, and registry contract tests.

The existing grader, interview event log, and mastery semantics remain
unchanged; only the three previously planned asset nodes are now catalog-ready.

## 8. Acceptance criteria

- Every P0/P1 card has all answer layers, ≥2 follow-ups, ≥2 pitfalls, mapped
  skills, and at least one source claim.
- At least one primary/official source supports each algorithmic claim; an
  anecdotal source never stands alone for a factual algorithm definition.
- Source URLs resolve, `checked_at` is present, and mutable sources include a
  version or commit field.
- Duplicate cards are linked rather than copied; CS336 coverage is referenced
  explicitly.
- Deterministic retrieval returns the same IDs for the same query, filters,
  and curriculum revision; active-session seed selection remains owned by the
  existing interview engine.
- A synthetic session can display provenance and report incomplete oral
  evidence without changing practice mastery/events.
- `git diff --check` and focused tests pass; full regression is run once at
  the integration gate.

## 9. Risks, rollback, and stop conditions

- **Stale APIs/branches:** pin a commit or mark the card volatile; block
  release when a source has materially changed and the claim is unreviewed.
- **Anecdotal overfitting:** keep report scope and confidence visible; never
  infer hiring guarantees from counts.
- **Copyright/privacy:** paraphrase, link, and remove copied personal details;
  delete/revert only the new content files if a takedown request arrives.
- **Schema drift:** additive migration only; a failed validator blocks import.
- **Scope creep:** stop if the work requires crawler credentials, external
  posting, public candidate prediction, or a change to Practice/mastery
  semantics.

Rollback is a revert of the implementation-phase content/index changes.  No
real Profile data is deleted automatically.

## 10. Progress and decision log

- [x] Initial source hierarchy, schema, and research policy drafted.
- [x] Domain coverage and file-impact plan identified.
- [x] Add reviewed card fixtures and source registry.
- [x] Implement deterministic retrieval and focused tests.
- [x] Perform focused content/licensing review and an integration-boundary run.
- [x] Add deep VLM, post-training, Agent/RAG, and inference research appendices.
- [x] Promote three self-contained multimodal/reward/scheduler exercises with
      contract-level validation and add 14 source-linked cards.

Decision log:

- 2026-08-30: use clean-room synthesis and source claims instead of copying
  public interview pages.
- 2026-08-30: keep oral cards separate from coding problem assets while
  linking them through skills and related problem IDs.
- 2026-08-30: keep the new bundle optional for old fixture repositories;
  `doctor --knowledge` opts into the additional validation.
- 2026-08-30: require coding prompts to carry an input/output/constraints
  contract, test focus, edge cases, and solution direction while leaving
  runnable answers in the existing Catalog problem assets.
