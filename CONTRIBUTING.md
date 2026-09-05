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

## Releasing

Maintainers only. Each release ships the PyPI package and the GitHub Action
from the same tag.

1. Bump `version` in `pyproject.toml`, `CITATION.cff`, and `.zenodo.json`,
   move the `Unreleased` notes in `CHANGELOG.md` under the new version, and
   update the `rev:` / `@vX.Y.Z` pins in `README.md`, `.pre-commit-hooks.yaml`,
   and `examples/`.
2. Merge to `main` with CI green, then tag `vX.Y.Z`. The publish workflow
   refuses a tag that does not match `pyproject.toml`.
3. Draft a GitHub release from that tag. To list the Action on GitHub
   Marketplace, tick "Publish this Action to the GitHub Marketplace" on the
   release form, confirm the metadata check passes, and pick a primary category
   (for example "Code quality"). Marketplace publishing requires a public
   repository, an action `name` that is unique on Marketplace, and two-factor
   authentication on the publishing account.
4. Publishing the release triggers `.github/workflows/publish.yml`, which builds
   the package and uploads it to PyPI through Trusted Publishing.

## PR expectations

- one logical change per PR
- clear explanation of any threshold or profile change
- no private data, private heuristics, or environment-specific paths
