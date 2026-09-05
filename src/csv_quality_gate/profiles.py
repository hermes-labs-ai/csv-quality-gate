from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any


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
    suspicious_warning_rate: float = 0.10
    suspicious_fail_rate: float = 0.30


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


def get_profile(name: str, profiles: Mapping[str, Profile] | None = None) -> Profile:
    """Resolve a profile by name, preferring ``profiles`` over the built-ins."""
    if profiles is not None and name in profiles:
        return profiles[name]
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unknown profile: {name}") from exc


def compile_patterns(patterns: tuple[str, ...]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


# --- project configuration -------------------------------------------------


class ConfigError(ValueError):
    """Raised when a project configuration file cannot be used."""


_COLUMN_LIST_KEYS = ("required_columns", "critical_columns", "suspicious_patterns")
_COLUMN_KEYS = ("duplicate_column", "suspicious_column")
_RATE_PAIRS = (
    ("empty_warning_rate", "empty_fail_rate"),
    ("duplicate_warning_rate", "duplicate_fail_rate"),
    ("suspicious_warning_rate", "suspicious_fail_rate"),
)
_PROFILE_KEYS = frozenset(field.name for field in fields(Profile) if field.name != "name")
_ALLOWED_PROFILE_KEYS = _PROFILE_KEYS | {"extends"}

# A custom profile that does not extend a built-in starts from these defaults:
# generic thresholds, no columns, no patterns.
_BLANK_PROFILE = replace(PROFILES["generic"], required_columns=(), critical_columns=(),
                         duplicate_column=None)


def load_config(path: Path) -> dict[str, Profile]:
    """Load project-specific profiles from a TOML or JSON configuration file.

    The file declares a ``profiles`` table whose keys are profile names. Each
    profile may set any :class:`Profile` field except ``name`` and may
    ``extends`` a built-in profile to inherit its values. Only data is accepted:
    column names, numeric thresholds, and regular-expression strings. The
    function never executes configuration content.

    Raises :class:`ConfigError` with a precise message on any problem.
    """
    data = _read_config_file(path)
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top-level value must be a table")
    unknown = sorted(set(data) - {"profiles"})
    if unknown:
        raise ConfigError(f"{path}: unknown top-level key(s): {', '.join(unknown)}")
    raw_profiles = data.get("profiles")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ConfigError(f"{path}: expected a non-empty [profiles] table")

    profiles: dict[str, Profile] = {}
    for name, raw in raw_profiles.items():
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"{path}: profile names must be non-empty strings")
        if not isinstance(raw, dict):
            raise ConfigError(f"{path}: profile {name!r} must be a table")
        try:
            profiles[name] = _build_profile(name, raw)
        except ConfigError as exc:
            raise ConfigError(f"{path}: profile {name!r}: {exc}") from None
    return profiles


def _read_config_file(path: Path) -> Any:
    suffix = path.suffix.lower()
    if suffix not in (".toml", ".json"):
        raise ConfigError(f"{path}: unsupported config format; use a .toml or .json file")
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raise ConfigError(f"{path}: config file not found") from None
    except IsADirectoryError:
        raise ConfigError(f"{path}: config path is a directory") from None
    try:
        if suffix == ".toml":
            try:
                import tomllib
            except ModuleNotFoundError:  # Python 3.10
                raise ConfigError(
                    f"{path}: TOML configuration needs Python 3.11+; "
                    "use a .json configuration on older interpreters"
                ) from None
            return tomllib.loads(raw.decode("utf-8"))
        return json.loads(raw)
    except UnicodeDecodeError as exc:
        raise ConfigError(f"{path}: config must be UTF-8: {exc}") from None
    except ValueError as exc:  # tomllib.TOMLDecodeError and json.JSONDecodeError
        raise ConfigError(f"{path}: cannot parse config: {exc}") from None


def _build_profile(name: str, raw: dict[str, Any]) -> Profile:
    unknown = sorted(set(raw) - _ALLOWED_PROFILE_KEYS)
    if unknown:
        raise ConfigError(f"unknown key(s): {', '.join(unknown)}")

    base = _BLANK_PROFILE
    if "extends" in raw:
        parent = raw["extends"]
        if not isinstance(parent, str) or parent not in PROFILES:
            raise ConfigError(
                f"extends must name a built-in profile ({', '.join(sorted(PROFILES))})"
            )
        base = PROFILES[parent]

    values: dict[str, Any] = {}
    for key in _COLUMN_LIST_KEYS:
        if key in raw:
            values[key] = _string_tuple(key, raw[key])
    for key in _COLUMN_KEYS:
        if key in raw:
            values[key] = _optional_string(key, raw[key])
    for warning_key, fail_key in _RATE_PAIRS:
        for key in (warning_key, fail_key):
            if key in raw:
                values[key] = _rate(key, raw[key])

    profile = replace(base, name=name, **values)

    for warning_key, fail_key in _RATE_PAIRS:
        if getattr(profile, warning_key) > getattr(profile, fail_key):
            raise ConfigError(f"{warning_key} must not exceed {fail_key}")
    for pattern in profile.suspicious_patterns:
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise ConfigError(f"invalid suspicious_patterns entry {pattern!r}: {exc}") from None
    return profile


def _string_tuple(key: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ConfigError(f"{key} must be a list of non-empty strings")
    if key == "suspicious_patterns":
        return tuple(value)  # regex text is significant, keep it verbatim
    return tuple(item.strip() for item in value)


def _optional_string(key: str, value: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise ConfigError(f"{key} must be a non-empty string")
    return value.strip()


def _rate(key: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigError(f"{key} must be a number between 0 and 1")
    rate = float(value)
    if not 0.0 <= rate <= 1.0:
        raise ConfigError(f"{key} must be a number between 0 and 1")
    return rate
