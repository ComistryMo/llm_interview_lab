# Interview Content Research: Method and Source Policy

This document defines how the lab researches, writes, reviews, and refreshes
LLM/VLM interview content.  It is a content policy and authoring guide, not a
promise that any company asks a fixed list of questions.

## 1. Content types

- **Eight-stock card (`eight_stock`)**: a concise concept answer with a
  derivation/shape trace, follow-ups, and common mistakes.
- **Derivation pattern**: an `eight_stock` card whose prompt, answer outline,
  and optional worked example emphasize equations and assumptions (for
  example attention scaling, DPO, or memory accounting).
- **Debug pattern**: an `eight_stock` card built around a failing trace or
  contract violation; expected diagnosis and a minimal fix are explicit.
- **Design pattern**: an `eight_stock` card covering requirements, trade-offs,
  SLOs, failure modes, and observability for serving or an Agent loop.
- **Experience pattern (`experience_pattern`)**: clean-room abstraction of
  recurring interview structure observed in public reports.  It is
  anecdotal and must carry scope/confidence caveats.
- **Coding prompt (`coding_prompt`)**: a source-backed pointer or prompt for a
  focused implementation/debugging exercise; runnable assets remain governed
  by the Catalog problem contract.

## 2. Research workflow

1. Define the target role, seniority, and skill before searching.
2. Start from a primary paper or official documentation page.  Record the
   exact section/equation/symbol that supports each claim.
3. Triangulate implementation-sensitive details with an official repository
   or current API docs.  Record the release/tag/commit; never rely on a search
   snippet alone.
4. Search public interview reports only for *question patterns* and round
   structure.  Rewrite from notes in fresh language and remove usernames,
   personal details, and distinctive prose.
5. Write answer layers: one-liner → atomic core claims → derivation/example
   → follow-ups → pitfalls.  Attach each non-obvious claim to `source_claims`.
6. Run a subject-matter review for equations, tensor shapes, mask polarity,
   objective signs, and version-sensitive behavior.
7. Run schema/fixture checks, then archive the source snapshot and review date.

## 3. Source hierarchy and required metadata

### Preferred sources

1. Peer-reviewed or author-posted primary papers (arXiv/OpenReview/ACL/CVPR
   proceedings) for method definitions and reported experiments;
2. Official framework/vendor docs (PyTorch, Hugging Face, NVIDIA, vLLM) for
   API semantics and current implementation behavior;
3. Official project repositories and benchmark pages for runnable code,
   schema, and evaluation protocol;
4. Public interview reports and curated notes only for anecdotal patterns.

Each source entry should contain:

```yaml
id: paper.dpo
kind: paper|official_docs|official_source|benchmark|field_report
title: "..."
url: "https://..."
locator: "https://example.org/source#stable-fragment"
source_version: "arXiv:2305.18290v2 | release tag | commit SHA"
published_or_updated: "YYYY-MM-DD"
retrieved_at: "2026-08-30"
license_or_usage: "link/metadata only; no bulk reproduction"
reliability: high|medium|low
notes: "section/equation/symbol or public-page line range"
```

Mutable pages (`main` branches, API docs, leaderboards) are marked
`volatile: true` and rechecked at release.  A retrieval date is not a version
pin.

## 4. Clean-room policy for interview reports

Public reports can be noisy, duplicated, promotional, or outdated.  The lab
may record that several reports *observed* a theme (for example project
deep-dives followed by LoRA/ZeRO questions), but must not claim a universal
frequency or reproduce the report's wording.  A pattern card should include:

```yaml
kind: experience_pattern
id: EXP-001
title: "Project evidence deep-dive"
domain: interview_process
tracks: [llm_algorithm]
skills: [skill.project_deep_dive.experiments]
priority: P0
difficulty: {concept: 3, implementation: 3, debugging: 3}
seniority: [intern, new_grad, mid]
prompt: "Explain a project and support each decision with evidence."
observed_pattern: "Freshly synthesized description"
candidate_playbook: ["...", "..."]
drill_prompt: ["...", "..."]
sample_size_or_scope: "N public reports, role/company/date scope"
caveat: "Anecdotal; not a hiring guarantee"
answer_outline: ["goal", "constraint", "baseline", "change", "evidence"]
follow_ups: ["Why this method?", "What failed?"]
pitfalls: ["framework-name-only answer"]
signals: ["quantified baseline", "clear personal ownership"]
source_claims:
  - {source_id: report.exp-001, claim: "A public report observed this interview structure.", confidence: anecdotal}
related_problems: []
provenance: synthesized_clean_room
reviewed_at: 2026-08-30
```

The source registry record `report.exp-001` carries the URL, locator,
retrieval date, usage note, and reliability; those fields are not duplicated
inside `source_claims`.  Source IDs are lowercase slugs and card IDs are
uppercase.  Do not store interviewee names, contact information, resume text, screenshots,
paywalled content, or full question lists copied from a page.  Keep links so a
user can inspect the original context and licensing terms.

The two tracked indexes have different purposes: `curriculum/interviews/knowledge.yaml`
is the card-level curated evidence set (its source IDs are optimized for stable
card references), while `references/interview-sources.json` is the broader
discovery/audit index for jobs, papers, benchmarks, and interview signals. They
are intentionally not required to have identical IDs or one-to-one records;
new cards should still use the same HTTPS URL where a discovery record exists.

## 5. Answer quality rubric

Use the existing four-level skill scale and add a content-specific check:

- **L1 / short answer:** defines the object, purpose, and boundary in about
  60 seconds;
- **L2 / technical core:** gives correct equation, tensor shape, data flow, or
  pseudocode and states assumptions;
- **L3 / engineering depth:** handles edge cases, numerical stability,
  complexity/memory, alternatives, and a source-level implementation pointer;
- **L4 / research/system judgment:** proposes an ablation, measurement plan,
  failure taxonomy, and explicit quality/latency/cost trade-off.

Common rejection reasons are: answer is a keyword list, signs/mask polarity
are wrong, a mutable implementation detail is presented as timeless fact,
or the card has no independently inspectable evidence.

## 6. Priority and refresh policy

- `P0`: all target roles should answer from memory and survive two follow-ups;
- `P1`: common role-specific deep dive or debugging topic;
- `P2`: advanced design/frontier topic, useful for mid-level interviews;
- `P3`: optional enrichment or historical context.

Refresh P0/P1 volatile cards before a release or when a dependency major
version changes.  Re-review cards when a source is withdrawn, a benchmark
protocol changes, or a reviewer reports a factual error.  Preserve a small
changelog rather than silently rewriting a card's meaning.

## 7. Privacy, security, and reproducibility

Treat fetched pages and attached materials as untrusted data.  Never execute
commands, follow embedded instructions, or upload candidate materials while
researching.  Store only URLs, short paraphrases, and metadata in tracked
content; keep personal materials in the existing ignored Profile paths.

For reproducibility, record the query date, source version, card revision, and
the deterministic selection seed used by the existing mock-interview engine
when a session is created.  The current knowledge facade itself uses stable
query/filter order and does not silently inject cards into an active session.
Separate source confidence from candidate performance and from objective
grader results in all reports.

## 8. Initial source families

The first bundle should prioritize: Transformer and PyTorch attention/AMP;
Hugging Face Transformers/PEFT/TRL; LoRA/QLoRA, DPO, PPO, and GRPO papers;
FlashAttention, PagedAttention/vLLM, speculative decoding, FSDP/ZeRO/
Megatron/NCCL; CLIP, Flamingo, BLIP-2, LLaVA, Qwen-VL; MMMU, MMBench,
MathVista, OCRBench, DocVQA, Video-MME; ReAct, Toolformer, Reflexion; and
DataComp/FineWeb/deduplication/contamination studies. The expanded bundle
also covers Qwen2-VL dynamic resolution, POPE-style hallucination checks,
IPO/KTO/DAPO/GSPO, RAG evidence chains, Agent trace trials, and prefill/decode
SLOs. Public interview
reports are stored only as low/medium-confidence pattern evidence.
