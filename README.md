# csv-quality-gate: CSV preflight validation before pipeline runs

Fail fast before pipeline runs when the input CSV is broken, incomplete, duplicated, or obviously junk.

`csv-quality-gate` runs batch CSV quality checks and returns `pass`, `warn`, or `fail` before expensive pipeline steps burn time on bad input.

- "We keep running expensive pipeline steps on broken CSVs."
- "A batch run fails 20 minutes in because the input CSV was junk."
- "We only discover missing required columns after the job already started."
- "Duplicate rows and empty contact fields keep polluting our batch runs."
- "I want CSV preflight validation, not a whole data platform."

Fastest install:

```bash
pip install csv-quality-gate
```

Fastest real usage:

```bash
csv-quality-gate check leads.csv --profile outreach
```

Exact outcome:

```text
csv-quality-gate: FAIL
file: leads.csv
profile: outreach
rows: 125
  ERROR: missing required column: person_name
  WARNING: duplicate rate 12% exceeds warning threshold 10%
```

![csv-quality-gate preview](assets/preview.png)

It is designed for narrow, honest use as a preflight gate, not as a full data quality platform.

## Install

```bash
pip install csv-quality-gate
```

For development:

```bash
pip install -e ".[dev]"
```

## Common search-intent use cases

- CSV preflight validation
- batch CSV quality checks
- fail fast before pipeline runs
- CSV validation before ETL or enrichment
- detect junk CSV rows before batch jobs

## Usage

```bash
csv-quality-gate check leads.csv
csv-quality-gate check leads.csv --profile outreach
csv-quality-gate check leads.csv --profile generic --json
```

Exit codes:

- `0` pass
- `1` warnings only
- `2` fail

## Profiles

Built-in profiles:

- `generic`
  - validates required columns, empties, duplicates, empty file
- `outreach`
  - adds suspicious company-name heuristics for GTM/contact pipelines

## Output

```text
csv-quality-gate: FAIL
file: leads.csv
profile: outreach
rows: 125
  ERROR: missing required column: person_name
  WARNING: duplicate rate 12% exceeds warning threshold 10%
```

## JSON mode

```bash
csv-quality-gate check leads.csv --json
```

## Limitations

- Heuristics are intentionally simple.
- The `outreach` profile is opinionated and should not be treated as universal truth.
- The tool validates shape and obvious noise, not semantic correctness.

## When To Use It

- Before enrichment, outreach, ETL, or batch scoring runs
- In CI for checked-in CSV inputs
- As a preflight gate before expensive pipeline work

## When Not To Use It

- When you need semantic validation of the data itself
- When your input is not CSV
- When you need a full data quality framework with lineage and profiling

## More From Hermes Labs

- [intent-verify](https://github.com/roli-lpci/intent-verify): repo intent verification and spec drift checks

## Development

```bash
ruff check .
python3 -m pytest -q
python3 -m py_compile src/csv_quality_gate/*.py
```
