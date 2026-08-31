from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .models import COMPARISON_SCHEMA_VERSION, EvidenceStatus
from .policy import Policy, is_blocking


SUPPORTED_REPORT_SCHEMAS = frozenset({"evidencelint-report-v1", "evidencelint-report-v2"})


class ChangeCategory(str, Enum):
    NEW_BLOCKER = "new_blocker"
    RESOLVED_BLOCKER = "resolved_blocker"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class ReportView:
    repository: str
    captured_at: str
    default_sha: str
    rule_set_version: str
    findings: dict[str, EvidenceStatus]


@dataclass(frozen=True)
class FindingChange:
    rule_id: str
    baseline: EvidenceStatus
    current: EvidenceStatus
    category: ChangeCategory

    def to_dict(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "baseline": self.baseline.value,
            "current": self.current.value,
            "category": self.category.value,
        }


@dataclass(frozen=True)
class ComparisonReport:
    baseline: ReportView
    current: ReportView
    policy_digest: str
    changes: tuple[FindingChange, ...]
    schema_version: str = COMPARISON_SCHEMA_VERSION

    def counts(self) -> dict[str, int]:
        return {
            category.value: sum(change.category is category for change in self.changes)
            for category in ChangeCategory
        }

    def new_blockers(self) -> tuple[FindingChange, ...]:
        return tuple(
            change
            for change in self.changes
            if change.category is ChangeCategory.NEW_BLOCKER
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repository": self.current.repository,
            "rule_set_version": self.current.rule_set_version,
            "policy_digest": self.policy_digest,
            "baseline": {
                "captured_at": self.baseline.captured_at,
                "default_sha": self.baseline.default_sha,
            },
            "current": {
                "captured_at": self.current.captured_at,
                "default_sha": self.current.default_sha,
            },
            "summary": self.counts(),
            "changes": [change.to_dict() for change in self.changes],
        }


def load_report(path: Path) -> ReportView:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"could not read report: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"report is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("report must be a JSON object")
    if payload.get("schema_version") not in SUPPORTED_REPORT_SCHEMAS:
        raise ValueError("report uses an unsupported schema_version")
    snapshot = payload.get("snapshot")
    findings = payload.get("findings")
    if not isinstance(snapshot, dict) or not isinstance(findings, list):
        raise ValueError("report must include snapshot and findings")
    repository = snapshot.get("repository")
    captured_at = snapshot.get("captured_at")
    default_sha = snapshot.get("default_sha")
    rule_set_version = payload.get("rule_set_version")
    if not all(
        isinstance(value, str) and value
        for value in (repository, captured_at, default_sha, rule_set_version)
    ):
        raise ValueError("report snapshot is incomplete")
    assert isinstance(repository, str)
    assert isinstance(captured_at, str)
    assert isinstance(default_sha, str)
    assert isinstance(rule_set_version, str)
    parsed_findings: dict[str, EvidenceStatus] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("report finding must be an object")
        rule_id = finding.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError("report finding has no rule_id")
        if rule_id in parsed_findings:
            raise ValueError(f"report contains duplicate rule_id: {rule_id}")
        try:
            parsed_findings[rule_id] = EvidenceStatus(finding.get("status"))
        except ValueError as exc:
            raise ValueError(f"report finding {rule_id} has unknown status") from exc
    return ReportView(repository, captured_at, default_sha, rule_set_version, parsed_findings)


def compare_reports(baseline: ReportView, current: ReportView, policy: Policy) -> ComparisonReport:
    if baseline.repository != current.repository:
        raise ValueError("reports must describe the same repository")
    if baseline.rule_set_version != current.rule_set_version:
        raise ValueError("reports must use the same rule_set_version")
    if set(baseline.findings) != set(current.findings):
        raise ValueError("reports must contain the same rule identifiers")
    changes: list[FindingChange] = []
    for rule_id in sorted(current.findings):
        before = baseline.findings[rule_id]
        after = current.findings[rule_id]
        before_blocking = is_blocking(rule_id, before, policy)
        after_blocking = is_blocking(rule_id, after, policy)
        if not before_blocking and after_blocking:
            category = ChangeCategory.NEW_BLOCKER
        elif before_blocking and not after_blocking:
            category = ChangeCategory.RESOLVED_BLOCKER
        elif before is after:
            category = ChangeCategory.UNCHANGED
        else:
            category = ChangeCategory.CHANGED
        changes.append(FindingChange(rule_id, before, after, category))
    return ComparisonReport(baseline, current, policy.digest, tuple(changes))
