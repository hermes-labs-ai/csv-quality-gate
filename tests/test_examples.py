"""Executable checks for the recipes under examples/ and the Action metadata.

Each recipe ships a custom profile plus one passing and one failing fixture; the
recipe document must name those fixtures so the docs cannot drift from the files.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
TOML_ONLY = pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib needs Python 3.11+")

# (recipe directory / document stem, profile, passing fixture, failing fixture)
RECIPES = [
    pytest.param(
        "dbt-seed", "seed", "seeds/country_codes.csv", "seeds-broken/country_codes.csv",
        id="dbt-seed",
    ),
    pytest.param(
        "promptfoo-dataset", "promptfoo", "tests.csv", "tests-broken.csv",
        id="promptfoo-dataset",
    ),
]


def run_gate(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "csv_quality_gate.cli", "check", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )


@TOML_ONLY
@pytest.mark.parametrize(("recipe", "profile", "passing", "failing"), RECIPES)
def test_recipe_fixtures_pass_and_fail(recipe, profile, passing, failing):
    cwd = EXAMPLES / recipe
    config = ("--config", "csv-quality-gate.toml", "--profile", profile)

    ok = run_gate(cwd, passing, *config)
    assert ok.returncode == 0, ok.stdout
    assert ok.stdout.startswith("csv-quality-gate: PASS")

    bad = run_gate(cwd, failing, *config)
    assert bad.returncode == 2, bad.stdout
    assert bad.stdout.startswith("csv-quality-gate: FAIL")
    assert "evidence: column=" in bad.stdout

    # The recipe quotes both reports verbatim; keep the quoted text honest.
    text = (EXAMPLES / f"{recipe}.md").read_text()
    assert ok.stdout.strip() in text, ok.stdout
    assert bad.stdout.strip() in text, bad.stdout


@pytest.mark.parametrize(("recipe", "profile", "passing", "failing"), RECIPES)
def test_recipe_document_names_its_fixtures_and_is_linked(recipe, profile, passing, failing):
    text = (EXAMPLES / f"{recipe}.md").read_text()
    for needle in (passing, failing, f"--profile {profile}"):
        assert needle in text, needle
    assert f"examples/{recipe}.md" in (ROOT / "README.md").read_text()


def test_action_metadata_declares_marketplace_branding():
    text = (ROOT / "action.yml").read_text()
    assert "author: Hermes Labs" in text
    assert "branding:" in text
    assert "icon: check-circle" in text
    assert "color: green" in text
