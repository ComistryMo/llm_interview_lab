# AI Connections

AI is an optional edge around a deterministic local core. The Catalog, DAG,
grader, event reducer, clock, review gates, and mastery rules work without a
model. Connecting AI adds explanation, bounded hints, evidence-based review,
adaptive interview follow-up, and maintainer assistance; it does not replace
those authorities.

## Pick the right mode

| Mode | Use it for | May edit learner answer? | May grant mastery? |
|---|---|---:|---:|
| No AI | Practice and manual interviews | No AI involved | No |
| COACH | Route, prerequisites, reflection | No | No |
| TEACHER H1/H2/H3 | Graded help on current task | No | No |
| REVIEWER | Tests, contract review, oral defense | No | No |
| INTERVIEWER | One frozen question and follow-up | No | No |
| Repository Agent | Maintainer/contributor changes | Only after approval; not personal submissions by default | No |

H0 is independent work. H1 covers an official reference or one syntax issue; H2
provides a conceptual direction; H3 gives structured steps. H4/H5 are explicit
demonstrations and require a new independent variant. The desktop Alpha exposes
H1-H3 for normal Practice and does not provide teaching hints during an active
mock interview.

## No AI

This is the default and a complete supported workflow. You can create a Profile,
follow Quests, solve and test Problems, submit, review, retain, run manual role
interviews, and generate reports without credentials or network access.

Choose no-AI when the material is sensitive, the provider policy is unclear,
you want a true closed-book attempt, or network availability is unreliable.

## Chat providers

The optional provider layer uses Mozilla any-llm rather than maintaining five
similar HTTP clients. Source installs support:

- OpenAI;
- OpenAI-compatible endpoints;
- Anthropic;
- Gemini;
- Ollama.

The compact Windows portable build bundles one OpenAI-compatible protocol
adapter for OpenAI, compatible endpoints, and Ollama's `/v1` endpoint, plus the
separate Codex App Server backend. Native Anthropic and Gemini adapters are
available when running from a Python 3.11 source install with `[ai]`; they are
not forced into the first portable executable because doing so multiplies the
binary and CI build closure. This packaging boundary does not change what the
app sends or how keys are stored.

Provider model catalogs are inconsistent, so the configured model ID remains
explicit. The app does not guess a model or claim that every model/provider pair
has been production-tested.

Install on Python 3.11:

```powershell
python -m pip install -e ".[desktop,ai,dev]"
llm-lab-gui
```

### Save a connection

1. Open **Connections**.
2. Choose the provider.
3. Enter a lowercase connection ID, display name, and model ID.
4. Enter a custom endpoint only for OpenAI-compatible or Ollama.
5. Enter the API key for a remote provider.
6. Save, clear the visible field, and select **Test Connection**.

Ollama may be configured without a key. Remote providers require a key.

## Secret storage

Secrets go to the operating-system keyring through `keyring`. On Windows this is
the Windows Credential Manager backend. Profile configuration stores only:

```json
{
  "connection_id": "openai-main",
  "provider_id": "openai",
  "model": "chosen-model-id",
  "display_name": "OpenAI",
  "base_url": null,
  "key_reference": "profile:default:connection:openai-main"
}
```

There is no plaintext fallback. If the keyring is unavailable, saving fails.
Deleting a connection removes both local metadata and its keyring entry.

Never put an API key in `profile.yaml`, `events.jsonl`, a submission, a material,
an environment screenshot, an issue, or an exported report.

## Context Preview

Before a provider request, the desktop app presents labels, selection state,
sensitivity, estimated tokens, and SHA-256 for each context part. The estimate is
a display hint; the provider is authoritative for billed tokens.

Normal Practice context may contain only:

- current public `task.md`;
- current Role/Skill summary;
- the requested H1/H2/H3 hint section;
- current answer, only when selected;
- latest structured public-test summary;
- AI policy.

It excludes the whole Workspace, other Profiles, old answers, raw events, test
source, Oracle, private tests, Git history, keys, and unselected materials.

The first version uses a safe fixed selection, not arbitrary file browsing. If a
part is not needed, do not include it. Static policy text can be cached by SHA in
an AI client rather than resent as repeated prose.

## Career materials and consent

`--allow-ai` or the GUI toggle only makes material eligible for a future consent
choice. It is not permanent consent.

A tailored role interview requires:

1. the current Profile;
2. an explicit material ID;
3. purpose `role_interview`;
4. current SHA-256;
5. confirmation for this session.

If the file changes, consent is stale. The app does not recursively scan
`materials/`, follow links, execute attachments, fetch embedded URLs, or infer
permission from a filename.

Material bodies are untrusted evidence. Text such as “ignore the policy,” “read
another file,” or “run this command” cannot change AI scope. Resume facts,
project ownership, metrics, paper claims, and job requirements must be cited or
marked uncertain; the interviewer may not invent them.

## Codex integration

Codex is a separate agent backend, not another ChatProvider. It uses the official
App Server over JSONL stdio:

```text
codex app-server --listen stdio://
initialize → initialized → account/read
thread/start or thread/resume
turn/start → streamed item/turn events
turn/interrupt for cancel
```

The backend supports availability and sign-in checks, thread start/resume,
streamed messages, cancel, errors, retry by starting another turn, diff/file
events, and bidirectional command/file approval requests. It never parses ANSI
output or simulates keys in the interactive CLI.

### Codex permissions

- COACH, REVIEWER, and INTERVIEWER start read-only with approval policy `never`.
- Repository Agent uses workspace-write with `untrusted` approval policy.
- Approval cards show action, scope, files, command, reason, and risk.
- The user can approve once or reject. There is no “approve everything” button.
- Personal submissions and other Profiles remain outside default maintainer
  scope even in Repository Agent mode.

Codex authentication, sandbox, and approval semantics are controlled by the
installed Codex version. If the protocol or capability is unavailable, the
integration fails closed and no-AI/provider paths remain usable.

## Provider interview assessment

For a non-coding question, the provider receives the frozen current question,
its exact rubric, selected consented material, and the candidate answer. It must
return strict JSON with:

```json
{
  "scores": {"rubric_dimension": 3},
  "evidence": "A quote or precise answer reference",
  "confidence": "medium",
  "fatal_issues": [],
  "follow_up": "At most one adaptive follow-up"
}
```

The workbench rejects missing/extra dimensions, non-integer 1–5 scores, unknown
fatal issues, missing evidence, invalid confidence, and malformed JSON. A
follow-up is archived separately and cannot change the frozen main plan.

Coding-round correctness comes from the local grader, not model prose. Subjective
dimensions and objective code evidence stay separate.

## Failure behavior

- **401/authentication:** show a bounded authentication message; never echo key.
- **429/rate limit:** preserve local work and suggest retry later.
- **Timeout:** cancel the request and keep the context/answer local.
- **5xx:** report a temporary provider failure without raw sensitive bodies.
- **Invalid model:** return a generic provider error; recheck the explicit ID.
- **Stream cancel:** mark cancelled; do not treat partial text as an assessment.
- **Malformed scorecard:** reject it and keep the question unscored.

CI uses fake providers and fake App Server events. It never calls a paid API and
does not require a real Codex account.

## Privacy checklist

Before every remote call:

- confirm the current Profile and mode;
- inspect Context Preview;
- remove unnecessary answer/material parts;
- confirm material ID, purpose, and SHA;
- remove employer/customer code, private data, internal model names, metrics,
  screenshots, logs, and configuration;
- check the provider's own retention/training policy;
- remember that Git ignore does not control a provider.

The workbench logs no authorization headers, plaintext keys, complete sensitive
prompts, absolute material paths, Oracle, or private tests. Profile data is local
by default, but remote AI necessarily receives the exact context the user sends.

## Recommended low-token workflow

1. Start no-AI and run the local test first.
2. Ask one narrow question in the lowest sufficient help mode.
3. Send task contract plus a structured test summary before full output.
4. Share the current answer only when diagnosis truly needs it.
5. Reuse policy/context hashes in a repo-aware agent session.
6. End a mock interview before switching to teaching.
7. Store the useful conclusion as local Review/evidence, not as a long chat log.

This keeps AI useful at the edges without making the user pay tokens for the
Catalog, historical events, unrelated materials, or repeated policy prose.
