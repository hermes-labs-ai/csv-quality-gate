from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path

from .models import GateResult, Issue, Severity, Status
from .profiles import ConfigError, Profile, get_profile, load_config
from .report import exit_code, to_json, to_json_many, to_text, to_text_many
from .validator import DEFAULT_MAX_EXAMPLES, validate_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-quality-gate",
        description="Run CSV preflight validation and fail fast before expensive pipeline runs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="run batch CSV quality checks on one or more files")
    check.add_argument("csv_path", nargs="+", help="path(s) to the csv file(s) to validate")
    check.add_argument(
        "--profile",
        default="generic",
        metavar="PROFILE",
        help="validation profile: a built-in (generic or outreach) or one from --config",
    )
    check.add_argument(
        "--config",
        metavar="FILE",
        help="TOML or JSON file declaring project-specific profiles under [profiles]",
    )
    check.add_argument(
        "--max-examples",
        type=_non_negative_int,
        default=DEFAULT_MAX_EXAMPLES,
        metavar="N",
        help=(
            "max affected row numbers listed per issue "
            f"(default {DEFAULT_MAX_EXAMPLES}; 0 lists none)"
        ),
    )
    check.add_argument("--json", action="store_true", help="emit machine-readable JSON output")
    return parser


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from None
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _error_result(path: Path, profile: str, message: str, config: str | None) -> GateResult:
    return GateResult(
        path=str(path),
        profile=profile,
        row_count=0,
        issues=[Issue(Severity.ERROR, message)],
        status=Status.FAIL,
        config=config,
    )


def _check_one(
    path: Path,
    profile: Profile | None,
    profile_name: str,
    error: str | None,
    max_examples: int,
    config: str | None,
) -> GateResult:
    if profile is None:
        return _error_result(path, profile_name, error or "no profile resolved", config)
    if not path.exists():
        return _error_result(path, profile_name, f"file not found: {path}", config)
    if not path.is_file():
        return _error_result(path, profile_name, f"path is not a file: {path}", config)
    return validate_csv(path, profile=profile, max_examples=max_examples, config=config)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    # Allow options between paths (`check a.csv --json b.csv`): argparse leaves
    # the trailing positionals in ``extras`` when a subparser is involved.
    args, extras = parser.parse_known_args(argv)
    unknown = [item for item in extras if item.startswith("-")]
    if unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")
    paths = [Path(item) for item in [*args.csv_path, *extras]]
    config: str | None = args.config

    profile: Profile | None = None
    error: str | None = None
    try:
        custom: Mapping[str, Profile] | None = None
        if config is not None:
            custom = load_config(Path(config))
        profile = get_profile(args.profile, custom)
    except ConfigError as exc:
        error = f"invalid config: {exc}"
    except ValueError as exc:  # unknown profile
        error = str(exc)

    results = [
        _check_one(path, profile, args.profile, error, args.max_examples, config)
        for path in paths
    ]

    if len(results) == 1:
        print(to_json(results[0]) if args.json else to_text(results[0]))
    else:
        print(to_json_many(results) if args.json else to_text_many(results))
    return max(exit_code(result) for result in results)


if __name__ == "__main__":
    raise SystemExit(main())
