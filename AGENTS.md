# AGENTS.md

## What this tool does

- Validates a CSV file before a batch pipeline runs.
- Checks required columns, empty critical fields, duplicate rates, and optional suspicious values.
- Returns `pass`, `warn`, or `fail`.

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
