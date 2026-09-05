# AGENTS.md

csv-quality-gate is a command-line data quality gate that runs CSV preflight validation and returns `pass`, `warn`, or `fail` before a pipeline ingests bad input. Stdlib-only, no third-party runtime dependencies.

## What this tool does

- Validates one or more CSV files before a batch pipeline runs.
- Checks required columns, empty files, empty critical fields, duplicate rates, and (outreach profile or custom config) suspicious values.
- Points every rate-based issue at affected line numbers (bounded, never cell values).
- Returns `pass`, `warn`, or `fail` with exit codes `0`, `1`, and `2`.
- Accepts project-specific profiles from a TOML/JSON file via `--config`.

## When to use it

- CSV preflight validation
- Batch CSV quality checks
- Before ETL, enrichment, outreach, or scoring jobs
- As a pre-commit hook (`.pre-commit-hooks.yaml`, id `csv-quality-gate`) or GitHub Action

## When not to use it

- Do not use it as semantic data verification.
- Do not use it for non-CSV inputs.
- Do not use it when you need lineage, profiling, or full data governance features.

## Minimal invocation

```bash
csv-quality-gate check leads.csv
csv-quality-gate check leads.csv --profile outreach
csv-quality-gate check leads.csv --json
csv-quality-gate check leads.csv --config csv-quality-gate.toml --profile leads
csv-quality-gate check a.csv b.csv --max-examples 0
```

## Expected output shape

Text mode:

- header with status
- file path
- profile (and config path when `--config` is used)
- row count
- one line per warning/error, followed by an indented `evidence:` line (column, affected count, line numbers) when rows back the issue
- one block per file when several paths are given

JSON mode:

- `path`
- `profile`
- `config` (only when `--config` is used)
- `rows`
- `status`
- `issues[]` of `{severity, message}` plus optional `evidence: {column, total, rows[]}`
- an array of these objects when several paths are given

## Known limitations

- simple heuristics
- outreach profile is opinionated
- validates obvious shape/noise problems, not semantic truth
- evidence is line numbers and counts only, never cell values
- TOML config needs Python 3.11+; JSON config works on 3.10

## Common failure cases

- file path does not exist
- wrong profile chosen for the dataset
- required column names do not match the actual schema (declare your own in `--config`)
- profile heuristics are too strict for the CSV being checked (tune thresholds in `--config`)
- config file rejected (unknown key, rate outside 0..1, warning rate above fail rate, bad regex)

## What counts as success

- `pass` means no issues
- `warn` means warnings only
- `fail` means at least one blocking issue

## Part of the Hermes Labs reliability stack

See https://github.com/hermes-labs-ai for the other open-source reliability tools. csv-quality-gate guards pipeline input data and complements, rather than replaces, the agent- and prompt-level tools in the stack.
