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
class Issue:
    severity: Severity
    message: str


@dataclass(frozen=True)
class GateResult:
    path: str
    profile: str
    row_count: int
    issues: list[Issue]
    status: Status
