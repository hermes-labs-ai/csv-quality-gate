# AGENTS.md

csv-quality-gate is a command-line data quality gate that runs CSV preflight validation and returns `pass`, `warn`, or `fail` before a pipeline ingests bad input. Stdlib-only, no third-party runtime dependencies.

## What this tool does

- Validates a single CSV file before a batch pipeline runs.
- Checks required columns, empty files, empty critical fields, duplicate rates, and (outreach profile) suspicious values.
- Returns `pass`, `warn`, or `fail` with exit codes `0`, `1`, and `2`.

## When to use it

- CSV preflight validation
- Batch CSV quality checks
- Before ETL, enrichment, outreach, or scoring jobs

## When not to use it

- Do not use it as semantic data verification.
- Do not use it for non-CSV inputs.
- Do not use it when you need lineage, profiling, or full data governance features.

## Minimal invocation

```bash
csv-quality-gate check leads.csv
csv-quality-gate check leads.csv --profile outreach
csv-quality-gate check leads.csv --json
```

## Expected output shape

Text mode:

- header with status
- file path
- profile
- row count
- one line per warning/error

JSON mode:

- `path`
- `profile`
- `rows`
- `status`
- `issues[]`

## Known limitations

- simple heuristics
- outreach profile is opinionated
- validates obvious shape/noise problems, not semantic truth

## Common failure cases

- file path does not exist
- wrong profile chosen for the dataset
- required column names do not match the actual schema
- profile heuristics are too strict for the CSV being checked

## What counts as success

- `pass` means no issues
- `warn` means warnings only
- `fail` means at least one blocking issue

## Part of the Hermes Labs reliability stack

See https://github.com/hermes-labs-ai for the other open-source reliability tools. csv-quality-gate guards pipeline input data and complements, rather than replaces, the agent- and prompt-level tools in the stack.
