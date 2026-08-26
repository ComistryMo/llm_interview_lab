# Security Policy

## Supported versions

Only the latest commit on `main` is supported during the alpha phase.

## Reporting a vulnerability or privacy issue

Do not open a public issue with exploit details, credentials, personal data, employer/client material, or local paths. Use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository) when it is enabled for this repository. If that channel is unavailable, contact the maintainer through the private contact method shown on the maintainer's GitHub profile and include only the minimum reproducible information.

You should receive an acknowledgement within seven days. The maintainer will validate impact, coordinate a fix, and disclose only after affected users have a reasonable migration path.

## Scope

Security-sensitive components include the handoff exporter, path handling, archive verification, state parsing, CI permissions, and documentation that could encourage unsafe disclosure. The exporter reduces accidental inclusion; it does not certify that text is safe to publish. Human review remains mandatory.

Never submit real secrets as test fixtures. Construct synthetic tokens at runtime and make them unmistakably fake.
