from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True)
class Evidence:
    """Bounded, privacy-conscious pointer to the rows behind an issue.

    ``rows`` holds physical line numbers in the CSV file (the header is line 1),
    capped by the caller's example limit. ``total`` is the full count of affected
    rows. Cell values are never included.
    """

    column: str
    total: int
    rows: tuple[int, ...] = ()


@dataclass(frozen=True)
class Issue:
    severity: Severity
    message: str
    evidence: Evidence | None = None


@dataclass(frozen=True)
class GateResult:
    path: str
    profile: str
    row_count: int
    issues: list[Issue]
    status: Status
    config: str | None = None
