from __future__ import annotations

import json

from .models import GateResult, Status


def to_text(result: GateResult) -> str:
    lines = [
        f"csv-quality-gate: {result.status.value.upper()}",
        f"file: {result.path}",
        f"profile: {result.profile}",
        f"rows: {result.row_count}",
    ]
    for issue in result.issues:
        lines.append(f"  {issue.severity.value.upper()}: {issue.message}")
    return "\n".join(lines)


def to_json(result: GateResult) -> str:
    return json.dumps(
        {
            "path": result.path,
            "profile": result.profile,
            "rows": result.row_count,
            "status": result.status.value,
            "issues": [
                {"severity": issue.severity.value, "message": issue.message}
                for issue in result.issues
            ],
        },
        indent=2,
    )


def exit_code(result: GateResult) -> int:
    return {
        Status.PASS: 0,
        Status.WARN: 1,
        Status.FAIL: 2,
    }[result.status]
