# Python Data Reliability Golden Quest — Alpha Trial

This trial is for real learners. Do not upload submissions, private tests,
Workspace files, employer data, names, company names, or email addresses.

## 1. Clone and install

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
python -m venv .venv
# Activate .venv, then:
python -m pip install -e .[dev]
```

## 2. Initialize a local Profile

```bash
llm-lab init --profile golden-trial --track ai_foundation
llm-lab doctor
```

The Profile stays in ignored `workspace/profiles/golden-trial/`.

## 3. Select Python Data Reliability

```bash
llm-lab graph --track ai_foundation
llm-lab next --profile golden-trial
llm-lab start FND-001 --profile golden-trial
```

Follow `next` through FND-001, FND-002, FND-003, FND-004, FND-005, and
FND-006. Each requires implementation, contract/oral review, D+2, and D+7.
The production clock enforces the due dates; do not copy an old submission into
a retention attempt.

## 4. Complete the Capstone

After all six nodes are `mastered`, `next` unlocks `CAP-FND-001 Hard Sample
Data Pipeline`. Complete its start/test/submit/review flow. The Capstone has no
Alpha.2 retention asset, so its completion status is `reviewed` rather than
`mastered`.

## 5. Submit feedback

Open a [Golden Quest feedback issue](https://github.com/ComistryMo/llm_interview_lab/issues/new?template=beta.yml).
Report only anonymous experience and sanitized command output. Maintainers count
a field run only after receiving a real-user report; automated tests never count.
