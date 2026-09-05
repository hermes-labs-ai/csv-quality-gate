from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from .models import Evidence, GateResult, Issue, Status


def to_text(result: GateResult) -> str:
    lines = [
        f"csv-quality-gate: {result.status.value.upper()}",
        f"file: {result.path}",
        f"profile: {result.profile}",
    ]
    if result.config is not None:
        lines.append(f"config: {result.config}")
    lines.append(f"rows: {result.row_count}")
    for issue in result.issues:
        lines.append(f"  {issue.severity.value.upper()}: {issue.message}")
        if issue.evidence is not None:
            lines.append(f"    {_evidence_text(issue.evidence)}")
    return "\n".join(lines)


def to_text_many(results: Iterable[GateResult]) -> str:
    return "\n\n".join(to_text(result) for result in results)


def to_json(result: GateResult) -> str:
    return json.dumps(to_dict(result), indent=2)


def to_json_many(results: Iterable[GateResult]) -> str:
    return json.dumps([to_dict(result) for result in results], indent=2)


def to_dict(result: GateResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "path": result.path,
        "profile": result.profile,
        "rows": result.row_count,
        "status": result.status.value,
        "issues": [_issue_dict(issue) for issue in result.issues],
    }
    if result.config is not None:
        payload["config"] = result.config
    return payload


def _issue_dict(issue: Issue) -> dict[str, Any]:
    payload: dict[str, Any] = {"severity": issue.severity.value, "message": issue.message}
    if issue.evidence is not None:
        payload["evidence"] = {
            "column": issue.evidence.column,
            "total": issue.evidence.total,
            "rows": list(issue.evidence.rows),
        }
    return payload


def _evidence_text(evidence: Evidence) -> str:
    noun = "row" if evidence.total == 1 else "rows"
    text = f"evidence: column={evidence.column} affected={evidence.total} {noun}"
    if evidence.rows:
        listed = ", ".join(str(line) for line in evidence.rows)
        text += f" at line(s) {listed}"
        remaining = evidence.total - len(evidence.rows)
        if remaining > 0:
            text += f" (+{remaining} more)"
    return text


def exit_code(result: GateResult) -> int:
    return {
        Status.PASS: 0,
        Status.WARN: 1,
        Status.FAIL: 2,
    }[result.status]
