from pathlib import Path

from csv_quality_gate.models import Status
from csv_quality_gate.validator import validate_csv

FIXTURES = Path(__file__).parent / "fixtures"


def test_generic_pass():
    result = validate_csv(FIXTURES / "clean.csv")
    assert result.status is Status.PASS


def test_generic_warn_duplicate_rate():
    result = validate_csv(FIXTURES / "duplicates.csv")
    assert result.status is Status.WARN
    assert any("duplicate rate" in issue.message for issue in result.issues)


def test_outreach_fail_missing_people():
    result = validate_csv(FIXTURES / "missing_people.csv", profile_name="outreach")
    assert result.status is Status.FAIL
    assert any("empty rate for person_name" in issue.message for issue in result.issues)


def test_outreach_fail_suspicious_company_values():
    result = validate_csv(FIXTURES / "junk_companies.csv", profile_name="outreach")
    assert result.status is Status.FAIL
    assert any("suspicious company rate" in issue.message for issue in result.issues)
