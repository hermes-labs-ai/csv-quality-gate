"""Static checks for the pre-commit hook definition.

The live `pre-commit try-repo` proof runs in CI (see .github/workflows/ci.yml)
because it needs pre-commit installed and a network-capable pip.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hook_definition_matches_cli_contract():
    text = (ROOT / ".pre-commit-hooks.yaml").read_text()
    assert "- id: csv-quality-gate" in text
    assert "entry: csv-quality-gate check" in text
    assert "language: python" in text
    assert "types: [csv]" in text
    assert "require_serial: true" in text


def test_example_config_pins_hook_id():
    text = (ROOT / "examples" / "pre-commit-config.yaml").read_text()
    assert "repo: https://github.com/hermes-labs-ai/csv-quality-gate" in text
    assert "id: csv-quality-gate" in text
