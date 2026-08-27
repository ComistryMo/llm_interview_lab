# INT-017 · Investigate Reward Hacking

## Scenario

A fictional policy's aggregate reward improves rapidly, but human reviewers report repetitive formatting, shallow reasoning, and a decline on a held-out task family.

## Primary question

Design an investigation that distinguishes true capability improvement from reward exploitation. Cover reward decomposition, verifier behavior, holdouts, counterfactual probes, human calibration, monitoring, and remediation.

## Constraints

- High reward is not itself evidence of task quality.
- The reward model and policy may share data artifacts.
- Do not tune against the final protected set.

## Follow-up axes

The interviewer may reveal multiple rewards, a rule verifier, sparse human labels, or a policy that learns formatting shortcuts.
