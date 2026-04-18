from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    required_columns: tuple[str, ...]
    critical_columns: tuple[str, ...]
    duplicate_column: str | None
    empty_warning_rate: float
    empty_fail_rate: float
    duplicate_warning_rate: float
    duplicate_fail_rate: float
    suspicious_column: str | None = None
    suspicious_patterns: tuple[str, ...] = ()


OUTREACH_SUSPICIOUS_PATTERNS = (
    r"^.{1,2}$",
    r"^.{50,}$",
    r"^\d+$",
    r"^(the|this|that|these|those)$",
    r"^(however|although|because|before|between)$",
    r"^(january|february|march|april|may|june|july|august|september|october|november|december)$",
    r"^(north|south|east|west|united|states|article|section|chapter)$",
)

PROFILES: dict[str, Profile] = {
    "generic": Profile(
        name="generic",
        required_columns=("company",),
        critical_columns=("company",),
        duplicate_column="company",
        empty_warning_rate=0.10,
        empty_fail_rate=0.30,
        duplicate_warning_rate=0.10,
        duplicate_fail_rate=0.25,
    ),
    "outreach": Profile(
        name="outreach",
        required_columns=("company", "person_name"),
        critical_columns=("company", "person_name"),
        duplicate_column="company",
        empty_warning_rate=0.30,
        empty_fail_rate=0.70,
        duplicate_warning_rate=0.10,
        duplicate_fail_rate=0.25,
        suspicious_column="company",
        suspicious_patterns=OUTREACH_SUSPICIOUS_PATTERNS,
    ),
}


def get_profile(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unknown profile: {name}") from exc


def compile_patterns(patterns: tuple[str, ...]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
