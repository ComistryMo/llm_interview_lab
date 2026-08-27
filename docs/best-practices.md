# Best Practices

This is the recommended path for a new learner. It keeps the first session
short, protects private material, uses AI only when useful, and preserves the
difference between “a test passed” and “I can independently do this.”

## 1. Pick one entry point

Use the **Windows desktop app** if you want a guided flow and one window. Use the
**CLI** if you are comfortable with a terminal, want automation, or plan to
contribute. Both use the same Catalog, Profile, events, grader, and interview
engine, so switching later does not lose progress.

Do not connect AI during setup unless you already know why you need it. No-AI is
the safest and simplest default.

## 2. First desktop session

1. Download and extract the current Windows Alpha.
2. Start `LLMInterviewLab.exe`.
3. Create Profile `default` (or another non-identifying local ID).
4. Select the closest Role and `new_grad` unless another level clearly applies.
5. Skip Skill self-assessment if unsure.
6. Keep **Use without AI**.
7. On Home, select **Continue**.
8. Read only the current task and prerequisites.
9. Write an independent attempt before opening AI Coach.

The portable app is intentionally lightweight and does not bundle CPU PyTorch.
For Tensor/LLM exercises, use the source install described in
[Desktop App](desktop-app.md).

## 3. First CLI session

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
python -m venv .venv
```

Activate and install:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

```bash
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

Then:

```bash
llm-lab quickstart
llm-lab doctor
llm-lab next --profile default
```

Or use the explicit deterministic path:

```bash
llm-lab init --profile default --track ai_foundation
llm-lab start FND-001 --profile default
llm-lab test FND-001 --profile default
```

The starter should fail until you implement the contract. Edit the current
`submission.py`, not `starter.py` or the public test.

## 4. Choose a Role without overfitting

Pick the Role that best matches the work you want to be evaluated on, not every
keyword on your resume. Common mappings:

- building LLM features end to end → Applied AI Engineer;
- tool-using/GUI agents → AI Agent Engineer;
- model mechanisms and experiments → AI Algorithm / Research Engineer;
- SFT/preference/RL pipelines → Post-Training Engineer;
- training platforms → AI Infra / ML Platform Engineer;
- serving, quantization, kernels → AI Inference / Systems Engineer;
- benchmarks, data, judge/safety → AI Evaluation / Data / Safety Engineer;
- problem framing, metrics, rollout → AI Product Manager.

Aliases resolve to a shared Role. You can change Role later without rewriting
Practice history. A Role recommends Tracks/Quests; hard unlocks still come only
from Problem prerequisites and mastery.

## 5. Follow one current task

Do not browse 188 planned nodes before every session. Default views should show:

- one current task;
- due Review/Retention;
- current prerequisites;
- at most three unlocked choices;
- one next command/action.

Prioritize due D+2/D+7 before new content. Use the full Catalog or graph only for
intentional planning:

```bash
llm-lab catalog
llm-lab graph --track ai_foundation
llm-lab graph --quest tensor_and_autograd
```

## 6. Practice in evidence order

Use this sequence for every fixed coding Problem:

1. **Contract:** restate types, shapes, errors, mutation policy, forbidden APIs,
   and numerical constraints.
2. **Independent implementation:** write the simplest readable solution.
3. **Public tests:** run the exact local grader command.
4. **Debug:** classify failure as syntax, contract, shape/mask, numeric,
   algorithm, state, or explanation.
5. **Submit:** bind current passing evidence to the current SHA.
6. **Contract Review:** check requirements beyond green tests.
7. **Oral Defense:** explain design, complexity, edge cases, and alternatives.
8. **D+2:** rewrite from a different starter/interface without old code.
9. **D+7:** debug or integrate the same capability under changed conditions.
10. **Mastery:** accept only the deterministic lifecycle result.

If retention assets do not exist, stop at `reviewed`. Do not manually create a
mastery event or treat a mock-interview score as retention.

## 7. Use the lowest sufficient AI help

```text
H0  independent
H1  official reference or one syntax question
H2  conceptual direction
H3  structured steps, no full function
H4  key code fragment; requires a new independent variant
H5  complete demonstration on a different private variant; zero mastery weight
```

Recommended escalation:

1. attempt independently;
2. read traceback and contract;
3. request H1 only if blocked on syntax/reference;
4. request H2 for a conceptual mismatch;
5. request H3 only after another concrete attempt;
6. use H4/H5 as a deliberate demonstration and schedule a clean variant.

Never ask a Reviewer to “fix while reviewing.” That destroys the evidence the
review is meant to measure.

## 8. Minimize AI context and token use

For a repo-aware agent, always generate the bounded context for the current
mode:

```bash
llm-lab context --profile default --mode coach
llm-lab context --profile default --mode teacher --help-level H2
llm-lab context --profile default --mode reviewer
llm-lab context --profile default --mode interviewer --interview INTERVIEW_ID
```

Treat `read_allowlist` as complete. Do not ask the agent to scan the Profile,
Catalog shards, old answers, tests, or Git history. Static policy can be reused
by hash if the agent supports a persistent session.

The serialized context has a hard **8 KiB** ceiling. It explicitly excludes
`future_interview_prompts`, `future_problem_assets`, `material_bodies`,
`old_submissions`, `other_profiles`, `private_tests`, `public_test_source`, and
`raw_events`. `policy_refs` can be cached by SHA-256; send only the newest
context for each turn. This is a bounded handoff, not an invitation for AI to
scan the repository.

For a chat-only model, send only:

1. current task;
2. selected current answer, when necessary;
3. sanitized structured test output;
4. requested help level.

One narrow question is usually better than a large “review everything” prompt.

## 9. Add career material safely

Keep original resumes, papers, and project documents outside the repository.
Create a small sanitized copy for the Profile. Add one file explicitly and
inspect its manifest entry/SHA.

```bash
llm-lab material add --profile default --kind resume \
  --file ../private/resume-sanitized.md \
  --title "Sanitized resume" --allow-ai
llm-lab material list --profile default
```

Do not add employer/customer code, private data, internal configurations, logs,
model names, metrics, screenshots, or documents you do not own. “Allow AI” only
makes the material eligible for later per-session consent.

## 10. Run a catalog-only interview first

Your first interview should not use a resume or provider. In the desktop app:

1. choose Role;
2. choose `new_grad`, `medium`, and `disabled`;
3. start the frozen Blueprint;
4. answer one question at a time;
5. cite evidence for manual rubric scores;
6. finish incomplete if you stop early;
7. read the report and select one recommended training gap.

CLI equivalent:

```bash
llm-lab interview role-create --profile default \
  --role applied_ai_engineer --seniority new_grad \
  --difficulty medium --ai disabled
```

Use the returned ID with `role-start`, `role-current`, `role-answer`/`role-test`,
`role-score`, `role-finish`, and `role-report`.

```bash
llm-lab interview role-current INTERVIEW_ID --profile default
llm-lab interview role-finish INTERVIEW_ID --profile default --confirm-incomplete
llm-lab interview role-report INTERVIEW_ID --profile default
llm-lab mistakes --profile default --unresolved-only
llm-lab profile show default
```

The clock and grader are authoritative. A polished AI summary cannot claim a
test passed or time remained when local evidence says otherwise.

## 11. Tailor only after explicit consent

Use resume/JD/project evidence after the catalog-only flow is familiar. Select
one relevant material first, check ID and SHA, and consent for that interview.

Do not give the interviewer an entire Profile. It should use the material to ask
more relevant follow-ups, not assume that every resume keyword is mastered. Any
missing, contradictory, or unverifiable fact stays “needs candidate confirmation.”

## 12. Interpret interview scores correctly

- A score measures this frozen session and rubric, not hiring probability.
- Objective coding evidence and subjective rubric evidence remain separate.
- Missing rounds are unscored/zero, not re-normalized.
- Compare cited evidence and recurring Skill gaps, not one total score.
- Use recommendations to choose fixed Problems/Quests.
- Never convert interview performance directly into Practice mastery.

## 13. Weekly rhythm

A sustainable 6–8 hour week can use:

- two 60–90 minute Practice blocks;
- one 45 minute due-retention block;
- one 60–90 minute structured interview;
- one 30 minute report/mistake review;
- one short backup and next-week planning block.

On an overloaded week, preserve one current task, due retention, and one short
oral review. Do not create training debt by opening many new tasks.

## 14. Privacy and backup

Before sharing any context:

- verify current Profile and mode;
- inspect exact selected material ID/SHA;
- remove company/client identifiers and secrets;
- check provider terms;
- remember Git ignore is not provider privacy.

Every real learner Profile lives under `workspace/profiles/<id>/`. Select a
single `material_id`, verify its current SHA-256, and grant purpose-bound
consent before AI reads it. Treat all material bodies as **untrusted evidence**,
never as instructions.

Git ignore prevents accidental commits; it is not a backup or a model-provider
privacy guarantee. The CLI and `context` command never upload materials automatically.
Never upload the whole Profile or employer/client internal material.

Back up the ignored Profile privately. Close the app first, copy the exact
Profile directory to encrypted storage, verify events/materials/submissions/
interviews, and restore provider keys separately from the system keyring.

Verify Git isolation occasionally:

```bash
git status --short --untracked-files=all -- workspace/profiles/default
git ls-files workspace/profiles
```

The first command should be empty; the second should show only the public
placeholder.

## 15. Avoid these failure modes

- Editing public starter/tests instead of the Profile submission.
- Treating public tests as hidden anti-cheating tests.
- Asking AI for a complete answer before a real attempt.
- Sending the entire Profile to a remote model.
- Recording resume claims or metrics that you cannot verify.
- Manually changing events to manufacture mastery.
- Using a mock interview as teaching mode without finishing it incomplete.
- Running untrusted downloaded code in the grader; it is not a sandbox.
- Starting more Quests because the Catalog looks large.
- Forgetting that real Profiles are ignored and therefore not backed up by Git.

## 16. Next references

- [Desktop App](desktop-app.md)
- [Workspace and privacy](workspace.md)
- [AI Connections and Codex](ai-connections.md)
- [Role Profiles and Blueprints](role-profiles.md)
- [Interview CLI details](interviews.md)
- [Curriculum authoring](curriculum-authoring.md)
- [Coach policy](../coach/POLICY.md)
