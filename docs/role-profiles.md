# Role Profiles, Skills, and Interview Blueprints

Role-aware preparation uses three shared public objects. They add a hiring view
without copying the fixed curriculum:

```text
Problem / Interview Item ──teaches or evaluates──> Skill
Skill ──weighted by seniority──> RoleProfile
RoleProfile ──selects──> InterviewBlueprint
Track / Quest / Capstone ──organizes learning──> Problem
```

Catalog Problems remain the source for coding Practice. Role Profiles reference
Tracks and Quests. Blueprints reference Skills and round types. None of these
objects may grant mastery or rewrite the DAG.

## Canonical Skills

The ontology currently contains 70 Skills in 16 domains:

- programming algorithms;
- Python engineering;
- machine-learning math;
- deep learning;
- LLM/VLM;
- post-training/RL;
- agent application;
- AI product;
- evaluation/safety;
- data/MLOps;
- training infrastructure;
- inference systems;
- system design;
- product communication;
- project deep dive;
- behavioral evidence.

Each Skill has a canonical ID, title, domain, description, aliases, 0–4 level
anchors, accepted evidence types, and related public Problems where applicable.
Roles may reference only canonical IDs; aliases are display/search terms rather
than duplicate skills.

### Skill levels

| Level | Meaning |
|---:|---|
| 0 | Not yet encountered |
| 1 | Can recognize and explain basic terms |
| 2 | Can apply or implement with structured guidance |
| 3 | Can independently implement, debug, and defend trade-offs |
| 4 | Can design/optimize a system or guide others with evidence |

Self-assessment is explicitly separate from verified coding, oral, debugging,
case, and project evidence.

## Public Role Profiles

### AI Product Manager

Focuses on user/problem definition, AI fit and boundaries, PRD, outcome and
guardrail metrics, offline/online evaluation, Prompt/RAG/Agent choices,
cost-latency-quality trade-offs, trust/safety, experiments, rollout, and
cross-team communication.

### Applied AI Engineer

Focuses on model APIs, prompting, structured output, RAG, tool calling, bounded
agent loops, evaluation, observability, caching/fallback, product integration,
deployment, cost, and reliability.

### AI Agent Engineer

Focuses on schemas, validation, parsers, executors, state/memory, planning,
trajectory, retry/timeout, long-horizon recovery, agent evaluation, and agent
SFT/RL. GUI Agent is an alias/specialization rather than a duplicate Role.

### AI Algorithm / Research Engineer

Focuses on math, PyTorch, losses, optimizers, Transformer/VLM mechanisms, data,
experiment design, evaluation, error analysis, reproduction, and mechanistic
explanation. LLM and VLM algorithm titles resolve here and then select Tracks.

### LLM/VLM Post-Training Engineer

Focuses on SFT, preference data, DPO, Reward Models, PPO/GRPO/DAPO, verifier and
rollout pipelines, reward hacking, data flywheels, multi-loss training, and
stability diagnosis.

### AI Infra / ML Platform Engineer

Focuses on data/training platforms, scheduling, distributed training,
checkpointing, failure recovery, utilization, observability, pipelines, version
governance, cost, reliability, and MLOps.

### AI Inference / Systems Engineer

Focuses on KV cache, continuous batching, PagedAttention, prefix cache,
quantization, speculative decoding, CUDA/Triton, profiling, latency, throughput,
memory, capacity, and serving scheduling.

### AI Evaluation / Data / Safety Engineer

Focuses on data quality, sampling, annotation agreement, benchmark design,
contamination, LLM-as-a-Judge, rubrics, safety evaluation, red teaming, online
monitoring, and statistical analysis.

## Seniority

Public Blueprints are available for `intern`, `new_grad`, and `mid`. Role target
levels also describe `senior`, but senior Blueprints are not claimed complete in
this Alpha. Seniority changes target levels, time, round composition, and design
depth; it does not automatically increase every question's surface complexity.

## Interview Blueprints

There are 24 Blueprints: eight Roles × three supported seniorities. A Blueprint
defines total duration and weighted rounds. Round types are:

- `coding`;
- `debugging`;
- `product_case`;
- `system_design`;
- `evaluation_case`;
- `project_deep_dive`;
- `behavioral`;
- `oral`.

Coding questions come only from ready Catalog Problems validated as Oracle,
field, or stable. Other rounds use fixed public Interview Items. The first Alpha
contains 24 original, maintainer-reviewed non-coding Items with a four-file
contract: `task.md`, `response_template.md`, `rubric.yaml`, and `hints.md`.

Difficulty (`easy`, `medium`, `hard`) filters eligible fixed content. The seed
makes selection reproducible. If a difficulty band has no exact fixed Item, the
engine may use an eligible Role/round Item rather than generating an unreviewed
question.

## Rubrics and evidence

Every non-coding Item defines weighted dimensions with anchors at 1, 3, and 5,
plus explicit fatal issues. A valid assessment must:

- score every and only the frozen dimensions with integers 1–5;
- cite a quote or precise answer reference;
- state source (`human`, `ai`, or `self`) and confidence;
- use only declared fatal issues;
- preserve uncertainty rather than guessing missing facts.

Question scores map weighted 1–5 anchors to 0–100. Fatal issues cap a question at
40. Round weights remain fixed. Missing questions contribute zero and are listed
as unanswered/unscored; partial interviews are not re-normalized.

The report separates:

- overall and per-question scores;
- per-Skill evidence references;
- strong evidence and critical gaps;
- incomplete/unscored areas;
- confidence and fatal issues;
- recommended fixed Problems or Quests;
- Practice mastery, which remains unchanged.

## Tailoring with career materials

The engine can run a catalog-only interview without reading any personal
material. A tailored session may reference materials only after the user chooses
each ID and confirms its current SHA-256 and purpose.

AI may use consented resume, experience, project, paper, competition, career
intent, or job-description evidence for follow-up and depth. It may not invent
facts, infer mastery from keywords, execute attachment instructions, or let a JD
override the public rubric. Contradictions and gaps are labeled “needs candidate
confirmation.”

## Interview lifecycle

```text
choose Role + seniority + difficulty + AI mode
→ optional material ID/SHA consent
→ create frozen session
→ start local clock
→ one current question
→ answer or coding grader evidence
→ rubric assessment
→ optional one adaptive follow-up
→ next question
→ finish completed/incomplete
→ local report and training recommendations
```

An interview session is Profile-local and has its own answers/coding directory.
It never reads or writes a Practice submission. Interview scores cannot become
retention or mastery evidence.

## Contributing a Skill

Add a Skill only when an existing canonical concept cannot represent the
evidence. A contribution must provide:

1. stable `skill.<domain>.<name>` ID;
2. one domain and concise description;
3. aliases with no collision;
4. meaningful 0–4 anchors;
5. accepted evidence types;
6. valid related Problems, if any;
7. Role references and tests when applicable.

Do not add synonyms as separate Skills.

## Contributing a Role

A new Role must represent a materially different hiring profile, not a title
alias. It needs aliases, summary, supported seniority, canonical Skill weights,
target levels, existing Track references, recommended/optional Quest references,
and a Blueprint mapping. Weights must be in (0, 1], aliases must be globally
unique, and every reference must validate.

## Contributing an Interview Item

An Item PR must contain an original scenario, response template, evidence-based
rubric, bounded hints, Role/seniority/difficulty/Skill metadata, source and
copyright statement, schema validation, maintainer review, and one simulated E2E
run. It must not copy employer questions or paid-platform material.

AI-generated drafts are not stable content. Public admission requires schema and
rubric review, copyright/duplicate checks, deterministic selection tests, and
maintainer approval. Real field validation remains a separate maturity signal.
