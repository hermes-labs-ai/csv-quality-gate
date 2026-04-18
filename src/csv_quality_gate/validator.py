from __future__ import annotations

import csv
from pathlib import Path

from .models import GateResult, Issue, Severity, Status
from .profiles import compile_patterns, get_profile


def validate_csv(path: Path, profile_name: str = "generic") -> GateResult:
    profile = get_profile(profile_name)
    issues: list[Issue] = []

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
        headers = tuple((field or "").strip() for field in (rows[0].keys() if rows else ()))

    missing = [column for column in profile.required_columns if column not in headers]
    for column in missing:
        issues.append(Issue(Severity.ERROR, f"missing required column: {column}"))

    if not rows:
        issues.append(Issue(Severity.ERROR, "csv has no data rows"))
        return GateResult(str(path), profile.name, 0, issues, Status.FAIL)

    for column in profile.critical_columns:
        if column not in headers:
            continue
        empty_count = sum(1 for row in rows if not (row.get(column) or "").strip())
        empty_rate = empty_count / len(rows)
        if empty_rate >= profile.empty_fail_rate:
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"empty rate for {column} is {empty_rate:.0%}, "
                    f"exceeds fail threshold {profile.empty_fail_rate:.0%}",
                )
            )
        elif empty_rate >= profile.empty_warning_rate:
            issues.append(
                Issue(
                    Severity.WARNING,
                    f"empty rate for {column} is {empty_rate:.0%}, "
                    f"exceeds warning threshold {profile.empty_warning_rate:.0%}",
                )
            )

    if profile.duplicate_column and profile.duplicate_column in headers:
        values = [
            (row.get(profile.duplicate_column) or "").strip().casefold()
            for row in rows
            if (row.get(profile.duplicate_column) or "").strip()
        ]
        duplicate_rate = (len(values) - len(set(values))) / len(rows)
        if duplicate_rate >= profile.duplicate_fail_rate:
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"duplicate rate {duplicate_rate:.0%} exceeds fail threshold "
                    f"{profile.duplicate_fail_rate:.0%}",
                )
            )
        elif duplicate_rate >= profile.duplicate_warning_rate:
            issues.append(
                Issue(
                    Severity.WARNING,
                    f"duplicate rate {duplicate_rate:.0%} exceeds warning threshold "
                    f"{profile.duplicate_warning_rate:.0%}",
                )
            )

    if profile.suspicious_column and profile.suspicious_column in headers:
        patterns = compile_patterns(profile.suspicious_patterns)
        suspicious = []
        for row in rows:
            value = (row.get(profile.suspicious_column) or "").strip()
            if any(pattern.search(value) for pattern in patterns):
                suspicious.append(value)
        suspicious_rate = len(suspicious) / len(rows)
        if suspicious_rate >= 0.30:
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"suspicious {profile.suspicious_column} rate is {suspicious_rate:.0%}",
                )
            )
        elif suspicious_rate >= 0.10:
            issues.append(
                Issue(
                    Severity.WARNING,
                    f"suspicious {profile.suspicious_column} rate is {suspicious_rate:.0%}",
                )
            )

    status = _status_for_issues(issues)
    return GateResult(str(path), profile.name, len(rows), issues, status)


def _status_for_issues(issues: list[Issue]) -> Status:
    if any(issue.severity is Severity.ERROR for issue in issues):
        return Status.FAIL
    if issues:
        return Status.WARN
    return Status.PASS
