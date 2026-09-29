from pathlib import Path

from csv_quality_gate.models import Evidence, Severity, Status
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


def test_zero_warning_threshold_means_any_occurrence_not_always(tmp_path):
    from dataclasses import replace

    from csv_quality_gate.profiles import PROFILES

    profile = replace(PROFILES["generic"], name="strict", duplicate_warning_rate=0.0)
    clean = tmp_path / "clean.csv"
    clean.write_text("company\nAcme\nBeacon\n")
    assert validate_csv(clean, profile=profile).status is Status.PASS
    dup = tmp_path / "dup.csv"
    dup.write_text("company\nAcme\nacme\nBeacon\nCarbon\nDelta\nEcho\nFoxtrot\nGolf\nHotel\nIndia\n")
    result = validate_csv(dup, profile=profile)
    assert result.status is Status.WARN
    assert result.issues[0].message == "duplicate rate 10% exceeds warning threshold 0%"


def test_invalid_utf8_is_a_fail_receipt_not_a_crash(tmp_path):
    path = tmp_path / "latin1.csv"
    path.write_bytes(b"company\nAcm\xe9\n")
    result = validate_csv(path)
    assert result.status is Status.FAIL
    assert [issue.message for issue in result.issues] == ["csv is not valid UTF-8"]
    assert result.row_count == 0


def test_padded_header_is_matched_and_read(tmp_path):
    path = tmp_path / "padded.csv"
    path.write_text("company \nAcme\nBeacon\nCarbon\nDelta\n")
    result = validate_csv(path)
    assert result.status is Status.PASS, result.issues


def test_header_only_file_reports_no_rows_without_false_missing_column(tmp_path):
    path = tmp_path / "header_only.csv"
    path.write_text("company\n")
    result = validate_csv(path)
    assert result.status is Status.FAIL
    assert [issue.message for issue in result.issues] == ["csv has no data rows"]


def test_empty_file_reports_missing_column_and_no_rows(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    result = validate_csv(path)
    assert [issue.message for issue in result.issues] == [
        "missing required column: company",
        "csv has no data rows",
    ]


def test_builtin_messages_unchanged_for_v0_2_fixtures():
    assert [i.message for i in validate_csv(FIXTURES / "duplicates.csv").issues] == [
        "duplicate rate 12% exceeds warning threshold 10%"
    ]
    assert [
        i.message
        for i in validate_csv(FIXTURES / "missing_people.csv", profile_name="outreach").issues
    ] == ["empty rate for person_name is 75%, exceeds fail threshold 70%"]
    assert [
        i.message
        for i in validate_csv(FIXTURES / "junk_companies.csv", profile_name="outreach").issues
    ] == ["suspicious company rate is 100%"]


def test_rows_with_extra_fields_fail_instead_of_silently_shifting_columns(tmp_path):
    # An unquoted comma in the company name shifts every later value one column
    # right; the real email lands beyond the header and was never checked.
    path = tmp_path / "shifted.csv"
    path.write_text(
        "company,person_name,email\n"
        "Acme, Inc,Jane Doe,jane@acme.example\n"
        "Delta Corp,Dan Moe,dan@delta.example\n"
        "Beta, LLC,Bob Roe,bob@beta.example\n",
        encoding="utf-8",
    )
    result = validate_csv(path, profile_name="outreach")
    assert result.status is Status.FAIL
    issue = next(i for i in result.issues if "more fields than the header" in i.message)
    assert issue.severity is Severity.ERROR
    assert issue.evidence == Evidence(column="*", total=2, rows=(2, 4))


def test_empty_trailing_fields_beyond_header_are_tolerated(tmp_path):
    # Trailing delimiters ("Acme,Jane,,") add only empty overflow: nothing shifted.
    path = tmp_path / "trailing.csv"
    path.write_text("company,person_name\nAcme,Jane,,\nBeta,Bob, \n", encoding="utf-8")
    result = validate_csv(path, profile_name="outreach")
    assert result.status is Status.PASS
    assert result.issues == []
