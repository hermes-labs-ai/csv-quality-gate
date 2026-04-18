# csv-quality-gate

`csv-quality-gate` is a deterministic validator for CSV inputs used in batch pipelines.

It catches common failure modes before expensive downstream steps run:

- missing required columns
- too many empty critical fields
- duplicate rate above threshold
- suspicious “junk” values in named columns
- empty files

It is designed for narrow, honest use as a preflight gate, not as a full data quality platform.

## Install

```bash
pip install csv-quality-gate
```

For development:

```bash
pip install -e ".[dev]"
```

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

## Example output

```text
csv-quality-gate: FAIL
file: leads.csv
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

## Development

```bash
ruff check .
python3 -m pytest -q
python3 -m py_compile src/csv_quality_gate/*.py
```
