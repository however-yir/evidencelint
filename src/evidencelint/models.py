from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


REPORT_SCHEMA_VERSION = "evidencelint-report-v1"
BATCH_SCHEMA_VERSION = "evidencelint-batch-report-v2"
RULE_SET_VERSION = "evidencelint-rules-v2"


class EvidenceStatus(str, Enum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    MISSING = "missing"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class ActionCategory(str, Enum):
    CONFIRMED_DEFECT = "confirmed_defect"
    COLLECTION_BLOCKER = "collection_blocker"
    REVIEW_REQUIRED = "review_required"
    EVIDENCE_GAP = "evidence_gap"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    dimension: str
    status: EvidenceStatus
    title: str
    detail: str
    evidence: tuple[str, ...] = ()

    def to_dict(self, *, include_evidence: bool = True) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "dimension": self.dimension,
            "status": self.status.value,
            "title": self.title,
            "detail": self.detail,
            "evidence": list(self.evidence) if include_evidence else [],
        }


@dataclass(frozen=True)
class PortfolioAction:
    repository: str
    visibility: str
    category: ActionCategory
    finding: Finding

    def to_dict(self) -> dict[str, Any]:
        include_evidence = self.visibility != "private"
        return {
            "repository": self.repository,
            "visibility": self.visibility,
            "category": self.category.value,
            **self.finding.to_dict(include_evidence=include_evidence),
        }


@dataclass(frozen=True)
class RepositorySnapshot:
    repository: str
    captured_at: str
    metadata: dict[str, Any]
    default_sha: str
    check_runs: tuple[dict[str, Any], ...]
    tree_paths: tuple[str, ...]
    tree_truncated: bool
    readme: str | None
    latest_release: dict[str, Any] | None
    release_tags: tuple[str, ...] = ()
    collection_issues: dict[str, str] = field(default_factory=dict)
    api_rate_limit: dict[str, Any] = field(default_factory=dict)

    def summary_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "captured_at": self.captured_at,
            "visibility": self.metadata.get("visibility"),
            "default_branch": self.metadata.get("default_branch"),
            "default_sha": self.default_sha,
            "fork": bool(self.metadata.get("fork")),
            "archived": bool(self.metadata.get("archived")),
            "primary_language": self.metadata.get("language"),
            "topics": list(self.metadata.get("topics") or []),
            "path_count": len(self.tree_paths),
            "tree_truncated": self.tree_truncated,
            "check_run_count": len(self.check_runs),
            "latest_release": (
                self.latest_release.get("tag_name") if self.latest_release else None
            ),
            "release_tag_count": len(self.release_tags),
            "collection_issues": dict(sorted(self.collection_issues.items())),
            "api_rate_limit": dict(sorted(self.api_rate_limit.items())),
        }

    def check_run_summary(self) -> dict[str, int]:
        accepted = {"success", "neutral", "skipped"}
        pending = sum(run.get("status") != "completed" for run in self.check_runs)
        failed = sum(
            run.get("status") == "completed" and run.get("conclusion") not in accepted
            for run in self.check_runs
        )
        success = sum(run.get("conclusion") == "success" for run in self.check_runs)
        accepted_other = len(self.check_runs) - pending - failed - success
        return {
            "total": len(self.check_runs),
            "success": success,
            "accepted_other": accepted_other,
            "pending": pending,
            "failed": failed,
        }


@dataclass(frozen=True)
class AuditReport:
    snapshot: RepositorySnapshot
    findings: tuple[Finding, ...]
    schema_version: str = REPORT_SCHEMA_VERSION
    rule_set_version: str = RULE_SET_VERSION

    def status_counts(self) -> dict[str, int]:
        counts = {status.value: 0 for status in EvidenceStatus}
        for finding in self.findings:
            counts[finding.status.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        include_evidence = self.snapshot.metadata.get("visibility") != "private"
        return {
            "schema_version": self.schema_version,
            "rule_set_version": self.rule_set_version,
            "snapshot": self.snapshot.summary_dict(),
            "summary": self.status_counts(),
            "current_ci": self.snapshot.check_run_summary(),
            "findings": [
                finding.to_dict(include_evidence=include_evidence)
                for finding in self.findings
            ],
        }


@dataclass(frozen=True)
class BatchReport:
    owner: str
    captured_at: str
    reports: tuple[AuditReport, ...]
    failures: dict[str, str] = field(default_factory=dict)
    api_rate_limit: dict[str, Any] = field(default_factory=dict)
    schema_version: str = BATCH_SCHEMA_VERSION
    rule_set_version: str = RULE_SET_VERSION

    def status_counts(self) -> dict[str, int]:
        counts = {status.value: 0 for status in EvidenceStatus}
        for report in self.reports:
            for status, value in report.status_counts().items():
                counts[status] += value
        return counts

    def check_run_summary(self) -> dict[str, int]:
        counts = {
            "total": 0,
            "success": 0,
            "accepted_other": 0,
            "pending": 0,
            "failed": 0,
        }
        for report in self.reports:
            for key, value in report.snapshot.check_run_summary().items():
                counts[key] += value
        return counts

    def action_items(self) -> tuple[PortfolioAction, ...]:
        category_by_status = {
            EvidenceStatus.FAILED: ActionCategory.CONFIRMED_DEFECT,
            EvidenceStatus.UNAVAILABLE: ActionCategory.COLLECTION_BLOCKER,
            EvidenceStatus.PARTIAL: ActionCategory.REVIEW_REQUIRED,
            EvidenceStatus.MISSING: ActionCategory.EVIDENCE_GAP,
        }
        category_rank = {
            category: rank for rank, category in enumerate(ActionCategory)
        }
        actions = (
            PortfolioAction(
                repository=report.snapshot.repository,
                visibility=str(report.snapshot.metadata.get("visibility") or "unknown"),
                category=category_by_status[finding.status],
                finding=finding,
            )
            for report in self.reports
            for finding in report.findings
            if finding.status in category_by_status
        )
        return tuple(
            sorted(
                actions,
                key=lambda item: (
                    category_rank[item.category],
                    item.repository.lower(),
                    item.finding.rule_id,
                ),
            )
        )

    def action_counts(self) -> dict[str, int]:
        counts = {category.value: 0 for category in ActionCategory}
        for item in self.action_items():
            counts[item.category.value] += 1
        return counts

    def repository_action_summary(self) -> dict[str, int]:
        actionable = {
            EvidenceStatus.FAILED,
            EvidenceStatus.UNAVAILABLE,
            EvidenceStatus.PARTIAL,
            EvidenceStatus.MISSING,
        }
        return {
            "total": len(self.reports),
            "public": sum(
                report.snapshot.metadata.get("visibility") == "public"
                for report in self.reports
            ),
            "private": sum(
                report.snapshot.metadata.get("visibility") == "private"
                for report in self.reports
            ),
            "without_actions": sum(
                not any(finding.status in actionable for finding in report.findings)
                for report in self.reports
            ),
            "with_confirmed_defects": sum(
                any(finding.status == EvidenceStatus.FAILED for finding in report.findings)
                for report in self.reports
            ),
            "with_evidence_gaps": sum(
                any(finding.status == EvidenceStatus.MISSING for finding in report.findings)
                for report in self.reports
            ),
            "with_review_required": sum(
                any(finding.status == EvidenceStatus.PARTIAL for finding in report.findings)
                for report in self.reports
            ),
            "with_collection_blockers": sum(
                any(finding.status == EvidenceStatus.UNAVAILABLE for finding in report.findings)
                for report in self.reports
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "rule_set_version": self.rule_set_version,
            "owner": self.owner,
            "captured_at": self.captured_at,
            "summary": {
                "repositories_discovered": len(self.reports) + len(self.failures),
                "repositories_audited": len(self.reports),
                "repositories_failed": len(self.failures),
                "findings": self.status_counts(),
                "current_ci": self.check_run_summary(),
                "repositories": self.repository_action_summary(),
            },
            "actions": {
                "counts": self.action_counts(),
                "items": [item.to_dict() for item in self.action_items()],
            },
            "api_rate_limit": dict(sorted(self.api_rate_limit.items())),
            "repositories": [report.to_dict() for report in self.reports],
            "failures": dict(sorted(self.failures.items())),
        }
