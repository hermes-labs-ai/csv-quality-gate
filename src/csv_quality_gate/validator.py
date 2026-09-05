from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

from .models import Evidence, GateResult, Issue, Severity, Status
from .profiles import Profile, compile_patterns, get_profile

DEFAULT_MAX_EXAMPLES = 5


def validate_csv(
    path: Path,
    profile_name: str = "generic",
    *,
    profile: Profile | None = None,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
    config: str | None = None,
) -> GateResult:
    """Validate one CSV file against a profile.

    ``profile`` overrides ``profile_name`` when given (for project-specific
    profiles loaded with :func:`csv_quality_gate.profiles.load_config`).
    ``max_examples`` caps how many affected line numbers each issue carries as
    evidence; ``0`` keeps the affected-row count but lists no rows.
    """
    if profile is None:
        profile = get_profile(profile_name)
    if max_examples < 0:
        raise ValueError("max_examples must be >= 0")
    issues: list[Issue] = []

    rows: list[dict[str, str | None]] = []
    line_numbers: list[int] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(row)
                line_numbers.append(reader.line_num)
            fieldnames = tuple(reader.fieldnames or ())
    except UnicodeDecodeError:
        issues.append(Issue(Severity.ERROR, "csv is not valid UTF-8"))
        return GateResult(str(path), profile.name, 0, issues, Status.FAIL, config)
    except csv.Error as exc:
        issues.append(Issue(Severity.ERROR, f"csv parse error: {exc}"))
        return GateResult(str(path), profile.name, 0, issues, Status.FAIL, config)

    # Map trimmed header names to the raw keys DictReader uses for row lookups,
    # so a padded header like "company " still counts as the "company" column.
    columns: dict[str, str] = {}
    for raw in fieldnames:
        columns.setdefault((raw or "").strip(), raw)

    for column in profile.required_columns:
        if column not in columns:
            issues.append(Issue(Severity.ERROR, f"missing required column: {column}"))

    if not rows:
        issues.append(Issue(Severity.ERROR, "csv has no data rows"))
        return GateResult(str(path), profile.name, 0, issues, Status.FAIL, config)

    def cell(row: dict[str, str | None], column: str) -> str:
        return (row.get(columns[column]) or "").strip()

    for column in profile.critical_columns:
        if column not in columns:
            continue
        empty_rows = [
            line for row, line in zip(rows, line_numbers, strict=True) if not cell(row, column)
        ]
        issue = _threshold_issue(
            column,
            empty_rows,
            len(rows),
            profile.empty_warning_rate,
            profile.empty_fail_rate,
            lambda rate, kind, threshold, column=column: (
                f"empty rate for {column} is {rate:.0%}, exceeds {kind} threshold {threshold:.0%}"
            ),
            max_examples,
        )
        if issue is not None:
            issues.append(issue)

    column = profile.duplicate_column
    if column and column in columns:
        seen: set[str] = set()
        duplicate_rows: list[int] = []
        for row, line in zip(rows, line_numbers, strict=True):
            value = cell(row, column).casefold()
            if not value:
                continue
            if value in seen:
                duplicate_rows.append(line)
            seen.add(value)
        issue = _threshold_issue(
            column,
            duplicate_rows,
            len(rows),
            profile.duplicate_warning_rate,
            profile.duplicate_fail_rate,
            lambda rate, kind, threshold: (
                f"duplicate rate {rate:.0%} exceeds {kind} threshold {threshold:.0%}"
            ),
            max_examples,
        )
        if issue is not None:
            issues.append(issue)

    column = profile.suspicious_column
    if column and column in columns:
        patterns = compile_patterns(profile.suspicious_patterns)
        suspicious_rows = [
            line
            for row, line in zip(rows, line_numbers, strict=True)
            if any(pattern.search(cell(row, column)) for pattern in patterns)
        ]
        issue = _threshold_issue(
            column,
            suspicious_rows,
            len(rows),
            profile.suspicious_warning_rate,
            profile.suspicious_fail_rate,
            lambda rate, kind, threshold, column=column: (
                f"suspicious {column} rate is {rate:.0%}"
            ),
            max_examples,
        )
        if issue is not None:
            issues.append(issue)

    status = _status_for_issues(issues)
    return GateResult(str(path), profile.name, len(rows), issues, status, config)


def _threshold_issue(
    column: str,
    affected: list[int],
    total: int,
    warning_rate: float,
    fail_rate: float,
    message: Callable[[float, str, float], str],
    max_examples: int,
) -> Issue | None:
    """Turn affected line numbers into a warning/error issue with bounded evidence.

    No affected rows never raises an issue, so a threshold of ``0.0`` means
    "any occurrence" rather than "always".
    """
    if not affected:
        return None
    rate = len(affected) / total
    if rate >= fail_rate:
        severity, kind, threshold = Severity.ERROR, "fail", fail_rate
    elif rate >= warning_rate:
        severity, kind, threshold = Severity.WARNING, "warning", warning_rate
    else:
        return None
    evidence = Evidence(column=column, total=len(affected), rows=tuple(affected[:max_examples]))
    return Issue(severity, message(rate, kind, threshold), evidence)


def _status_for_issues(issues: list[Issue]) -> Status:
    if any(issue.severity is Severity.ERROR for issue in issues):
        return Status.FAIL
    if issues:
        return Status.WARN
    return Status.PASS
