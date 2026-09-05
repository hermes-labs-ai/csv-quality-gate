from __future__ import annotations

import argparse
from pathlib import Path

from .models import GateResult, Issue, Severity, Status
from .profiles import PROFILES
from .report import exit_code, to_json, to_text
from .validator import validate_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-quality-gate",
        description="Run CSV preflight validation and fail fast before expensive pipeline runs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="run batch CSV quality checks on one file")
    check.add_argument("csv_path", help="path to the csv file to validate")
    check.add_argument(
        "--profile",
        default="generic",
        metavar="PROFILE",
        help="validation profile (generic or outreach)",
    )
    check.add_argument("--json", action="store_true", help="emit machine-readable JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    path = Path(args.csv_path)
    if args.profile not in PROFILES:
        result = GateResult(
            path=str(path),
            profile=args.profile,
            row_count=0,
            issues=[Issue(Severity.ERROR, f"unknown profile: {args.profile}")],
            status=Status.FAIL,
        )
        print(to_json(result) if args.json else to_text(result))
        return exit_code(result)
    if not path.exists():
        result = GateResult(
            path=str(path),
            profile=args.profile,
            row_count=0,
            issues=[Issue(Severity.ERROR, f"file not found: {path}")],
            status=Status.FAIL,
        )
        print(to_json(result) if args.json else to_text(result))
        return exit_code(result)
    if not path.is_file():
        result = GateResult(
            path=str(path),
            profile=args.profile,
            row_count=0,
            issues=[Issue(Severity.ERROR, f"path is not a file: {path}")],
            status=Status.FAIL,
        )
        print(to_json(result) if args.json else to_text(result))
        return exit_code(result)
    result = validate_csv(path, profile_name=args.profile)
    print(to_json(result) if args.json else to_text(result))
    return exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
