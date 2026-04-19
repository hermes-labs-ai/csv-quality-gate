# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a suspected security problem.

Instead:

- email the maintainer directly
- include reproduction steps
- include impact assessment if known

## Scope

This project is a local CLI for CSV preflight validation. Relevant reports include:

- unsafe file handling
- malformed CSV inputs causing security-impacting behavior
- command execution or path traversal risks

Out of scope:

- disagreements about thresholds
- non-security false positives or false negatives
