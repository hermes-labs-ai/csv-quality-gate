# Contributing

Thanks for contributing.

## Before opening a PR

- keep the tool focused on CSV preflight validation
- prefer deterministic checks over hidden heuristics
- update tests with any behavior change
- update `README.md`, `AGENTS.md`, and `llms.txt` if the CLI behavior changes

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Local checks

```bash
ruff check .
pytest -q
python3 -m py_compile src/csv_quality_gate/*.py
```

## PR expectations

- one logical change per PR
- clear explanation of any threshold or profile change
- no private data, private heuristics, or environment-specific paths
