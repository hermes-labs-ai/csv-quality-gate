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


def test_cli_single_path_json_shape_is_unchanged_from_v0_2():
    result = run_cli("check", str(FIXTURES / "clean.csv"), "--json")
    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "path": str(FIXTURES / "clean.csv"),
        "profile": "generic",
        "rows": 4,
        "status": "pass",
        "issues": [],
    }


def test_cli_json_issue_carries_bounded_evidence():
    result = run_cli(
        "check", str(FIXTURES / "junk_companies.csv"), "--profile", "outreach", "--json",
        "--max-examples", "3",
    )
    assert result.returncode == 2
    [issue] = json.loads(result.stdout)["issues"]
    assert issue["evidence"] == {"column": "company", "total": 4, "rows": [2, 3, 4]}


def test_cli_rejects_negative_max_examples():
    result = run_cli("check", str(FIXTURES / "clean.csv"), "--max-examples", "-1")
    assert result.returncode == 2
    assert "must be >= 0" in result.stderr


def test_cli_multiple_paths_emit_json_array_and_max_exit_code():
    result = run_cli(
        "check", str(FIXTURES / "clean.csv"), str(FIXTURES / "duplicates.csv"), "--json"
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert [item["status"] for item in payload] == ["pass", "warn"]
    assert [item["path"] for item in payload] == [
        str(FIXTURES / "clean.csv"),
        str(FIXTURES / "duplicates.csv"),
    ]


def test_cli_multiple_paths_text_blocks_and_fail_wins():
    result = run_cli(
        "check",
        str(FIXTURES / "duplicates.csv"),
        str(FIXTURES / "clean.csv"),
        "missing.csv",
    )
    assert result.returncode == 2
    blocks = result.stdout.rstrip("\n").split("\n\n")
    assert [block.splitlines()[0] for block in blocks] == [
        "csv-quality-gate: WARN",
        "csv-quality-gate: PASS",
        "csv-quality-gate: FAIL",
    ]


def test_cli_custom_profile_from_config():
    config = str(FIXTURES / "project.json")
    passing = run_cli(
        "check", str(FIXTURES / "leads_pass.csv"), "--config", config, "--profile", "leads",
        "--json",
    )
    assert passing.returncode == 0
    payload = json.loads(passing.stdout)
    assert (payload["status"], payload["profile"], payload["config"]) == ("pass", "leads", config)

    failing = run_cli(
        "check", str(FIXTURES / "leads_fail.csv"), "--config", config, "--profile", "leads"
    )
    assert failing.returncode == 2
    assert "suspicious email rate is 60%" in failing.stdout
    assert f"config: {config}" in failing.stdout


def test_cli_builtin_profiles_still_work_with_config():
    result = run_cli(
        "check", str(FIXTURES / "clean.csv"), "--config", str(FIXTURES / "project.json"),
        "--json",
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["profile"] == "generic"


def test_cli_unknown_profile_with_config_fails_with_receipt():
    result = run_cli(
        "check", str(FIXTURES / "clean.csv"), "--config", str(FIXTURES / "project.json"),
        "--profile", "nope", "--json",
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["issues"] == [{"severity": "error", "message": "unknown profile: nope"}]


def test_cli_invalid_config_fails_with_receipt(tmp_path):
    config = tmp_path / "bad.json"
    config.write_text('{"profiles": {"x": {"empty_fail_rate": 2}}}')
    result = run_cli("check", str(FIXTURES / "clean.csv"), "--config", str(config), "--json")
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    [issue] = payload["issues"]
    assert issue["message"].startswith(f"invalid config: {config}: profile 'x': ")
    assert result.stderr == ""


def test_cli_missing_config_file_fails_with_receipt():
    result = run_cli("check", str(FIXTURES / "clean.csv"), "--config", "absent.toml", "--json")
    assert result.returncode == 2
    [issue] = json.loads(result.stdout)["issues"]
    assert issue["message"] == "invalid config: absent.toml: config file not found"


def test_cli_accepts_options_between_paths():
    result = run_cli(
        "check", str(FIXTURES / "clean.csv"), "--json", str(FIXTURES / "duplicates.csv")
    )
    assert result.returncode == 1
    assert [item["status"] for item in json.loads(result.stdout)] == ["pass", "warn"]


def test_cli_still_rejects_unknown_options():
    result = run_cli("check", str(FIXTURES / "clean.csv"), "--bogus")
    assert result.returncode == 2
    assert "unrecognized arguments: --bogus" in result.stderr
    assert result.stdout == ""
