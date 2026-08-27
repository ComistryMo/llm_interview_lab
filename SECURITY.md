# Security Policy

## Supported versions

Only the latest commit on `main` is supported during the alpha phase.

## Reporting a vulnerability or privacy issue

Do not open a public issue with exploit details, credentials, personal data, employer/client material, or local paths. Use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository) when it is enabled for this repository. If that channel is unavailable, contact the maintainer through the private contact method shown on the maintainer's GitHub profile and include only the minimum reproducible information.

You should receive an acknowledgement within seven days. The maintainer will validate impact, coordinate a fix, and disclose only after affected users have a reasonable migration path.

## Scope and trust boundary

Security-sensitive components include Workspace Git isolation, event parsing, submission path validation, the local pytest subprocess, external-course checkout verification, and CI permissions.

`llm-lab test` executes the learner's own local Python submission. Containment checks, unique module names, a timeout, and output truncation prevent common mistakes; they are not a sandbox and do not protect against malicious code. Do not use the grader for untrusted multi-tenant execution.

Real Profile data under `workspace/profiles/` is ignored by Git. Never force-add it, and never submit real secrets, employer data, private model names, internal metrics, or personal records as fixtures. Public demos and tests must be entirely synthetic.
