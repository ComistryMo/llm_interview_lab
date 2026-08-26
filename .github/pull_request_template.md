## Why


## What changed


## Verification

```text
python -m pytest -q
python scripts/validate_curriculum.py
python scripts/validate_state.py
```

## Checklist

- [ ] This PR solves one bounded problem and updates only the necessary authoritative files.
- [ ] I ran the relevant commands and reported failures honestly.
- [ ] Curriculum changes include prerequisites, visible tests, hints, oral questions, and D+2/D+7 variants.
- [ ] Curriculum metadata and generated navigation are synchronized; runtime/GPU policy is explicit.
- [ ] I did not include a complete learner solution or answer-leaking test.
- [ ] I did not include credentials, personal data, local paths, or employer/client material.
- [ ] Any material external influence is pinned and registered, or I explained why registration is unnecessary.
- [ ] AI-assisted content was reviewed for accuracy, licensing, and privacy by a human contributor.
