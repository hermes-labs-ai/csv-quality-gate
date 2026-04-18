from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .profiles import PROFILES
from .report import exit_code, to_json, to_text
from .validator import validate_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="csv-quality-gate")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="validate one csv file")
    check.add_argument("csv_path", help="path to csv file")
    check.add_argument(
        "--profile",
        default="generic",
        choices=sorted(PROFILES),
        help="validation profile",
    )
    check.add_argument("--json", action="store_true", help="emit JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    path = Path(args.csv_path)
    if not path.exists():
        print(f"csv-quality-gate: file not found: {path}", file=sys.stderr)
        return 2
    result = validate_csv(path, profile_name=args.profile)
    print(to_json(result) if args.json else to_text(result))
    return exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
