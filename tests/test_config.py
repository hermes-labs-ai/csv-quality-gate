import json
import sys
from pathlib import Path

import pytest

from csv_quality_gate.models import Status
from csv_quality_gate.profiles import PROFILES, ConfigError, Profile, get_profile, load_config
from csv_quality_gate.validator import validate_csv

FIXTURES = Path(__file__).parent / "fixtures"
TOML_ONLY = pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib needs Python 3.11+")


@pytest.fixture(params=["project.toml", "project.json"])
def config_path(request):
    if request.param.endswith(".toml") and sys.version_info < (3, 11):
        pytest.skip("tomllib needs Python 3.11+")
    return FIXTURES / request.param


def test_load_config_returns_profiles(config_path):
    profiles = load_config(config_path)
    assert set(profiles) == {"leads", "minimal"}
    leads = profiles["leads"]
    assert isinstance(leads, Profile)
    assert leads.name == "leads"
    assert leads.required_columns == ("email", "company")
    assert leads.critical_columns == ("email",)
    assert leads.duplicate_column == "email"
    assert leads.suspicious_patterns == ("^[^@]+$",)
    assert leads.suspicious_fail_rate == 0.50


def test_toml_and_json_configs_are_equivalent():
    if sys.version_info < (3, 11):
        pytest.skip("tomllib needs Python 3.11+")
    assert load_config(FIXTURES / "project.toml") == load_config(FIXTURES / "project.json")


def test_profile_without_extends_starts_blank_with_generic_thresholds(config_path):
    minimal = load_config(config_path)["minimal"]
    generic = PROFILES["generic"]
    assert minimal.required_columns == ("id",)
    assert minimal.critical_columns == ()
    assert minimal.duplicate_column is None
    assert minimal.suspicious_column is None
    assert minimal.empty_fail_rate == generic.empty_fail_rate
    assert minimal.duplicate_fail_rate == generic.duplicate_fail_rate


@pytest.mark.parametrize(
    ("fixture", "status", "fragment"),
    [
        ("leads_pass.csv", Status.PASS, None),
        ("leads_warn.csv", Status.WARN, "duplicate rate 20%"),
        ("leads_fail.csv", Status.FAIL, "suspicious email rate is 60%"),
    ],
)
def test_custom_profile_pass_warn_fail(config_path, fixture, status, fragment):
    profile = load_config(config_path)["leads"]
    result = validate_csv(FIXTURES / fixture, profile=profile)
    assert result.status is status
    assert result.profile == "leads"
    if fragment is not None:
        assert any(fragment in issue.message for issue in result.issues)
    else:
        assert result.issues == []


def test_custom_profile_reports_missing_required_columns(config_path):
    profile = load_config(config_path)["leads"]
    result = validate_csv(FIXTURES / "clean.csv", profile=profile)
    assert result.status is Status.FAIL
    assert [issue.message for issue in result.issues] == ["missing required column: email"]


def test_get_profile_prefers_custom_over_builtin():
    custom = {"generic": Profile("generic", ("id",), (), None, 0.1, 0.3, 0.1, 0.25)}
    assert get_profile("generic", custom) is custom["generic"]
    assert get_profile("outreach", custom) is PROFILES["outreach"]
    with pytest.raises(ValueError, match="unknown profile: nope"):
        get_profile("nope", custom)


def test_builtin_profiles_are_unchanged():
    generic = PROFILES["generic"]
    outreach = PROFILES["outreach"]
    assert (generic.required_columns, generic.duplicate_column) == (("company",), "company")
    assert (generic.empty_warning_rate, generic.empty_fail_rate) == (0.10, 0.30)
    assert (generic.duplicate_warning_rate, generic.duplicate_fail_rate) == (0.10, 0.25)
    assert outreach.required_columns == ("company", "person_name")
    assert (outreach.empty_warning_rate, outreach.empty_fail_rate) == (0.30, 0.70)
    assert (outreach.suspicious_warning_rate, outreach.suspicious_fail_rate) == (0.10, 0.30)
    assert len(outreach.suspicious_patterns) == 7


def _write(tmp_path: Path, name: str, body) -> Path:
    path = tmp_path / name
    if name.endswith(".json"):
        path.write_text(json.dumps(body))
    else:
        path.write_text(body)
    return path


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ({"profiles": {"x": {"required_columns": ["a"], "bogus": 1}}}, "unknown key"),
        ({"profiles": {"x": {"required_columns": "a"}}}, "list of non-empty strings"),
        ({"profiles": {"x": {"required_columns": [""]}}}, "list of non-empty strings"),
        ({"profiles": {"x": {"empty_fail_rate": 1.5}}}, "between 0 and 1"),
        ({"profiles": {"x": {"empty_fail_rate": "0.5"}}}, "between 0 and 1"),
        ({"profiles": {"x": {"empty_fail_rate": True}}}, "between 0 and 1"),
        (
            {"profiles": {"x": {"empty_warning_rate": 0.9, "empty_fail_rate": 0.5}}},
            "empty_warning_rate must not exceed empty_fail_rate",
        ),
        ({"profiles": {"x": {"suspicious_patterns": ["("]}}}, "invalid suspicious_patterns"),
        ({"profiles": {"x": {"extends": "nope"}}}, "extends must name a built-in"),
        ({"profiles": {"x": {"duplicate_column": 3}}}, "non-empty string"),
        ({"profiles": {"x": "not a table"}}, "must be a table"),
        ({"profiles": {}}, "non-empty \\[profiles\\] table"),
        ({"profile": {}}, "unknown top-level key"),
        ([], "top-level value must be a table"),
    ],
)
def test_invalid_config_is_rejected(tmp_path, body, match):
    path = _write(tmp_path, "bad.json", body)
    with pytest.raises(ConfigError, match=match):
        load_config(path)


def test_config_errors_name_file_and_profile(tmp_path):
    path = _write(tmp_path, "bad.json", {"profiles": {"leads": {"nope": 1}}})
    with pytest.raises(ConfigError) as info:
        load_config(path)
    assert str(info.value).startswith(f"{path}: profile 'leads': ")


def test_unparseable_config_is_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    with pytest.raises(ConfigError, match="cannot parse config"):
        load_config(path)


@TOML_ONLY
def test_unparseable_toml_is_rejected(tmp_path):
    path = _write(tmp_path, "bad.toml", "[profiles.x\nrequired_columns = 1")
    with pytest.raises(ConfigError, match="cannot parse config"):
        load_config(path)


def test_missing_and_unsupported_config_paths(tmp_path):
    with pytest.raises(ConfigError, match="config file not found"):
        load_config(tmp_path / "absent.json")
    with pytest.raises(ConfigError, match="unsupported config format"):
        load_config(_write(tmp_path, "profiles.yaml", "profiles: {}"))
    (tmp_path / "dir.json").mkdir()
    with pytest.raises(ConfigError, match="is a directory"):
        load_config(tmp_path / "dir.json")


@pytest.mark.skipif(sys.version_info >= (3, 11), reason="only relevant without tomllib")
def test_toml_config_explains_python_version_requirement(tmp_path):
    with pytest.raises(ConfigError, match="needs Python 3.11"):
        load_config(_write(tmp_path, "p.toml", "[profiles.x]\n"))


def test_config_cannot_carry_executable_content(tmp_path):
    # Only data keys are accepted; anything resembling code is an unknown key.
    path = _write(tmp_path, "bad.json", {"profiles": {"x": {"exec": "import os"}}})
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(path)


def test_column_names_are_trimmed_but_patterns_are_verbatim(tmp_path):
    path = _write(
        tmp_path,
        "cfg.json",
        {
            "profiles": {
                "x": {
                    "required_columns": [" email "],
                    "duplicate_column": "email ",
                    "suspicious_column": "  ",
                    "suspicious_patterns": ["^ x$"],
                }
            }
        },
    )
    profile = load_config(path)["x"]
    assert profile.required_columns == ("email",)
    assert profile.duplicate_column == "email"
    assert profile.suspicious_column is None
    assert profile.suspicious_patterns == ("^ x$",)
