import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "csv_quality_gate.cli", *args],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_json_warn():
    result = run_cli("check", str(FIXTURES / "duplicates.csv"), "--json")
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "warn"


def test_cli_fail():
    result = run_cli("check", str(FIXTURES / "missing_people.csv"), "--profile", "outreach")
    assert result.returncode == 2
    assert "FAIL" in result.stdout
