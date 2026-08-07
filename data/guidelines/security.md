# Security Review Guidelines

These are the review rules the security agent should apply. Content is generic
and intentionally free of any real credentials or proprietary details.

## Injection and deserialization

- Never pass untrusted input to `eval()` or `exec()`.
- Use parameterized queries for SQL; never concatenate user input into SQL strings.
- Prefer argument lists over `shell=True` in subprocess calls.
- Do not unpickle untrusted data with `pickle.loads`; prefer JSON or an allow-list.

## Secrets handling

- Never commit passwords, API keys, tokens, or connection strings to source.
- Load secrets from environment variables or a secret manager, never from code.
- Treat any hardcoded `api_key`, `password`, `token`, or `secret` as a finding.

## Transport and verification

- Do not disable TLS certificate verification (`verify=False`); it enables
  man-in-the-middle attacks.
- Pin dependency versions in lockfiles and re-audit third-party code.

## What triggers a human checkpoint

- Critical severity issues always pause the run for a human decision.
- High-severity findings delivered with low confidence also pause for review.
