import json
from pathlib import Path

import pytest

from csv_quality_gate.models import Evidence, Issue, Severity, Status
from csv_quality_gate.profiles import PROFILES, load_config
from csv_quality_gate.report import to_dict, to_json, to_text
from csv_quality_gate.validator import validate_csv

FIXTURES = Path(__file__).parent / "fixtures"


def _only_issue(result) -> Issue:
    assert len(result.issues) == 1
    return result.issues[0]


def test_duplicate_evidence_points_at_second_occurrence():
    result = validate_csv(FIXTURES / "duplicates.csv")
    issue = _only_issue(result)
    assert issue.evidence == Evidence(column="company", total=1, rows=(3,))


def test_empty_evidence_lists_affected_lines():
    result = validate_csv(FIXTURES / "missing_people.csv", profile_name="outreach")
    issue = _only_issue(result)
    assert issue.severity is Severity.ERROR
    assert issue.evidence == Evidence(column="person_name", total=3, rows=(2, 3, 4))


def test_suspicious_evidence_lists_affected_lines():
    result = validate_csv(FIXTURES / "junk_companies.csv", profile_name="outreach")
    issue = _only_issue(result)
    assert issue.evidence == Evidence(column="company", total=4, rows=(2, 3, 4, 5))


def test_line_numbers_follow_physical_lines_for_multiline_records():
    # Row 1 spans lines 2-3, so the duplicate "Acme" on the next record is line 4.
    result = validate_csv(FIXTURES / "multiline.csv")
    assert result.status is Status.WARN
    assert _only_issue(result).evidence == Evidence(column="company", total=1, rows=(4,))


@pytest.mark.parametrize(("limit", "rows"), [(0, ()), (1, (2,)), (2, (2, 3)), (5, (2, 3, 4))])
def test_max_examples_caps_rows_but_keeps_total(limit, rows):
    result = validate_csv(
        FIXTURES / "missing_people.csv", profile_name="outreach", max_examples=limit
    )
    evidence = _only_issue(result).evidence
    assert evidence is not None
    assert evidence.total == 3
    assert evidence.rows == rows


def test_negative_max_examples_is_rejected():
    with pytest.raises(ValueError, match="max_examples"):
        validate_csv(FIXTURES / "clean.csv", max_examples=-1)


def test_issues_without_row_evidence_keep_the_v0_2_json_shape():
    result = validate_csv(FIXTURES / "clean.csv", profile_name="outreach")
    payload = to_dict(result)
    assert payload["issues"] == [
        {"severity": "error", "message": "missing required column: person_name"}
    ]
    assert "config" not in payload
    assert set(payload) == {"path", "profile", "rows", "status", "issues"}


def test_json_evidence_shape_and_no_cell_values():
    result = validate_csv(FIXTURES / "leads_fail.csv", profile=load_config(
        FIXTURES / "project.json")["leads"], config="project.json")
    payload = json.loads(to_json(result))
    assert payload["config"] == "project.json"
    [issue] = payload["issues"]
    assert issue["evidence"] == {"column": "email", "total": 3, "rows": [3, 4, 5]}
    serialized = to_json(result)
    for value in ("bob-at-example", "cy example com", "dee", "ada@example.com", "Acme"):
        assert value not in serialized


def test_text_evidence_line_is_bounded_and_value_free():
    result = validate_csv(FIXTURES / "junk_companies.csv", profile_name="outreach", max_examples=2)
    text = to_text(result)
    assert "    evidence: column=company affected=4 rows at line(s) 2, 3 (+2 more)" in text
    for value in ("The", "However", "2025", "United"):
        assert value not in text.replace("threshold", "")


def test_text_evidence_without_rows_reports_count_only():
    result = validate_csv(FIXTURES / "duplicates.csv", max_examples=0)
    assert "    evidence: column=company affected=1 row" in to_text(result)
    assert "line(s)" not in to_text(result)


def test_text_report_shows_config_when_present():
    profile = PROFILES["generic"]
    result = validate_csv(FIXTURES / "clean.csv", profile=profile, config="cfg.toml")
    lines = to_text(result).splitlines()
    assert lines[:5] == [
        "csv-quality-gate: PASS",
        f"file: {FIXTURES / 'clean.csv'}",
        "profile: generic",
        "config: cfg.toml",
        "rows: 4",
    ]
