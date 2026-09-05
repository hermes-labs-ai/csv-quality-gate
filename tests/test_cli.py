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


def test_cli_missing_file_json_receipt_shape():
    result = run_cli("check", "missing.csv", "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "fail"


def test_cli_directory_path_json_receipt_shape():
    result = run_cli("check", str(FIXTURES), "--json")
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["issues"] == [
        {"severity": "error", "message": f"path is not a file: {FIXTURES}"}
    ]
    assert result.stderr == ""


def test_cli_unknown_profile_json_receipt_shape():
    result = run_cli("check", str(FIXTURES / "clean.csv"), "--profile", "unsupported", "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "fail"
