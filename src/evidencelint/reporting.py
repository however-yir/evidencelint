from __future__ import annotations

import json

from .comparison import ComparisonReport
from .models import ActionCategory, AuditReport, BatchReport, EvidenceStatus


ACTION_HEADINGS = {
    ActionCategory.CONFIRMED_DEFECT: "Confirmed defects",
    ActionCategory.COLLECTION_BLOCKER: "Collection blockers",
    ActionCategory.REVIEW_REQUIRED: "Review required",
    ActionCategory.EVIDENCE_GAP: "Evidence gaps",
}


def render(report: AuditReport, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    if output_format == "markdown":
        return render_markdown(report)
    if output_format == "text":
        return render_text(report)
    raise ValueError(f"unsupported output format: {output_format}")


def render_batch(report: BatchReport, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    if output_format == "markdown":
        return render_batch_markdown(report)
    if output_format == "text":
        return render_batch_text(report)
    raise ValueError(f"unsupported output format: {output_format}")


def render_comparison(report: ComparisonReport, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    if output_format == "markdown":
        return render_comparison_markdown(report)
    if output_format == "text":
        return render_comparison_text(report)
    raise ValueError(f"unsupported output format: {output_format}")


def render_text(report: AuditReport) -> str:
    snapshot = report.snapshot
    counts = report.status_counts()
    lines = [
        f"EvidenceLint audit: {snapshot.repository}",
        f"Captured: {snapshot.captured_at}",
        f"Default SHA: {snapshot.default_sha[:12]}",
        f"Schema: {report.schema_version}",
        f"Rule set: {report.rule_set_version}",
        "Summary: " + ", ".join(f"{key}={value}" for key, value in counts.items() if value),
        "",
    ]
    for finding in report.findings:
        lines.append(f"[{finding.status.value.upper()}] {finding.rule_id} - {finding.title}")
        lines.append(f"  {finding.detail}")
        evidence_items = (
            finding.evidence
            if snapshot.metadata.get("visibility") != "private"
            else ()
        )
        for evidence in evidence_items:
            lines.append(f"  evidence: {evidence}")
    if report.policy is not None:
        lines.extend(
            [
                "",
                "Policy: "
                f"{report.policy.source}, advisory={len(report.policy.advisory_rules)}, "
                f"blocking={len(report.policy.blocking_rule_ids)}",
            ]
        )
    return "\n".join(lines)


def render_markdown(report: AuditReport) -> str:
    snapshot = report.snapshot
    lines = [
        f"# EvidenceLint report: `{snapshot.repository}`",
        "",
        f"- Captured: `{snapshot.captured_at}`",
        f"- Default SHA: `{snapshot.default_sha}`",
        f"- Schema: `{report.schema_version}`",
        f"- Rule set: `{report.rule_set_version}`",
        "",
        "| Status | Dimension | Rule | Finding |",
        "|---|---|---|---|",
    ]
    for finding in report.findings:
        detail = finding.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{finding.status.value}` | {finding.dimension} | `{finding.rule_id}` | {detail} |"
        )
    lines.extend(["", "## Evidence locators", ""])
    for finding in report.findings:
        if finding.evidence and snapshot.metadata.get("visibility") != "private":
            lines.append(f"- `{finding.rule_id}`: " + ", ".join(f"`{item}`" for item in finding.evidence))
    if report.policy is not None:
        lines.extend(
            [
                "",
                "## Policy",
                "",
                f"- Source: `{report.policy.source}`",
                f"- Digest: `{report.policy.digest}`",
                "- Advisory rules: "
                + (", ".join(f"`{rule_id}`" for rule_id in report.policy.advisory_rules) or "none"),
                "- Blocking rules: "
                + (", ".join(f"`{rule_id}`" for rule_id in report.policy.blocking_rule_ids) or "none"),
            ]
        )
    return "\n".join(lines)


def render_batch_text(report: BatchReport) -> str:
    findings = report.status_counts()
    ci = report.check_run_summary()
    actions = report.action_counts()
    repositories = report.repository_action_summary()
    lines = [
        f"EvidenceLint batch audit: {report.owner}",
        f"Captured: {report.captured_at}",
        f"Schema: {report.schema_version}",
        f"Rule set: {report.rule_set_version}",
        (
            f"Repositories: audited={len(report.reports)}, "
            f"failed={len(report.failures)}"
        ),
        "Findings: " + ", ".join(
            f"{key}={value}" for key, value in findings.items() if value
        ),
        (
            "Current CI: "
            f"total={ci['total']}, success={ci['success']}, "
            f"accepted_other={ci['accepted_other']}, "
            f"pending={ci['pending']}, failed={ci['failed']}"
        ),
        (
            "Actions: "
            f"confirmed_defect={actions['confirmed_defect']}, "
            f"collection_blocker={actions['collection_blocker']}, "
            f"review_required={actions['review_required']}, "
            f"evidence_gap={actions['evidence_gap']}"
        ),
        f"Repositories without actions: {repositories['without_actions']}",
        "",
    ]
    for audit_report in report.reports:
        counts = audit_report.status_counts()
        repo_ci = audit_report.snapshot.check_run_summary()
        lines.append(
            f"{audit_report.snapshot.repository}: checks={repo_ci['total']} "
            f"verified={counts['verified']} partial={counts['partial']} "
            f"missing={counts['missing']} failed={counts['failed']} "
            f"unavailable={counts['unavailable']}"
        )
    if report.action_items():
        lines.extend(["", "Action queue:"])
        for action_item in report.action_items():
            lines.append(
                f"[{action_item.category.value.upper()}] {action_item.repository} "
                f"{action_item.finding.rule_id} - {action_item.finding.detail}"
            )
    if report.failures:
        lines.extend(["", "Collection failures:"])
        for repository, error in sorted(report.failures.items()):
            lines.append(f"- {repository}: {error}")
    return "\n".join(lines)


def render_batch_markdown(report: BatchReport) -> str:
    ci = report.check_run_summary()
    actions = report.action_counts()
    repositories = report.repository_action_summary()
    lines = [
        f"# EvidenceLint portfolio report: `{report.owner}`",
        "",
        f"- Captured: `{report.captured_at}`",
        f"- Schema: `{report.schema_version}`",
        f"- Rule set: `{report.rule_set_version}`",
        f"- Repositories audited: `{len(report.reports)}`",
        f"- Collection failures: `{len(report.failures)}`",
        (
            f"- Current CI: `{ci['success']}/{ci['total']}` success, "
            f"`{ci['pending']}` pending, `{ci['failed']}` failed"
        ),
        (
            f"- Action queue: `{actions['confirmed_defect']}` confirmed defects, "
            f"`{actions['collection_blocker']}` collection blockers, "
            f"`{actions['review_required']}` reviews, "
            f"`{actions['evidence_gap']}` evidence gaps"
        ),
        f"- Repositories without actions: `{repositories['without_actions']}`",
        "",
        "## Action queue",
        "",
        (
            "`confirmed_defect` means current evidence contradicts the expected "
            "condition; `collection_blocker` means the audit could not conclude; "
            "`review_required` means evidence is incomplete; `evidence_gap` means "
            "an expected artifact is absent, not that the project is broken."
        ),
        "",
    ]
    action_items = report.action_items()
    if not action_items:
        lines.extend(["No action items were identified.", ""])
    for category in ActionCategory:
        matching = tuple(item for item in action_items if item.category == category)
        if not matching:
            continue
        lines.extend(
            [
                f"### {ACTION_HEADINGS[category]}",
                "",
                "| Repository | Rule | Finding | Evidence |",
                "|---|---|---|---|",
            ]
        )
        for action_item in matching:
            payload = action_item.to_dict()
            detail = action_item.finding.detail.replace("|", "\\|").replace("\n", " ")
            evidence = ", ".join(
                str(value).replace("|", "\\|").replace("\n", " ")
                for value in payload["evidence"]
            )
            lines.append(
                f"| `{action_item.repository}` | `{action_item.finding.rule_id}` | "
                f"{detail} | {evidence} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Repository matrix",
            "",
            "| Repository | Visibility | Checks | Verified | Partial | Missing | Failed | Unavailable |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for audit_report in report.reports:
        counts = audit_report.status_counts()
        snapshot = audit_report.snapshot
        lines.append(
            f"| `{snapshot.repository}` | {snapshot.metadata.get('visibility', '')} | "
            f"{len(snapshot.check_runs)} | {counts['verified']} | {counts['partial']} | "
            f"{counts['missing']} | {counts['failed']} | {counts['unavailable']} |"
        )
    if report.failures:
        lines.extend(["", "## Collection failures", ""])
        for repository, error in sorted(report.failures.items()):
            safe_error = error.replace("\n", " ")
            lines.append(f"- `{repository}`: {safe_error}")
    return "\n".join(lines)


def strict_exit_code(report: AuditReport) -> int:
    if report.policy is not None:
        return 1 if report.policy.blocking_rule_ids else 0
    blocked = {EvidenceStatus.FAILED, EvidenceStatus.MISSING}
    return 1 if any(finding.status in blocked for finding in report.findings) else 0


def batch_strict_exit_code(report: BatchReport) -> int:
    if report.failures:
        return 1
    return 1 if any(strict_exit_code(item) for item in report.reports) else 0


def comparison_strict_exit_code(report: ComparisonReport) -> int:
    return 1 if report.new_blockers() else 0


def render_comparison_text(report: ComparisonReport) -> str:
    counts = report.counts()
    lines = [
        f"EvidenceLint comparison: {report.current.repository}",
        f"Baseline SHA: {report.baseline.default_sha[:12]}",
        f"Current SHA: {report.current.default_sha[:12]}",
        f"Rule set: {report.current.rule_set_version}",
        "Summary: " + ", ".join(f"{key}={value}" for key, value in counts.items() if value),
        "",
    ]
    for change in report.changes:
        if change.category.value != "unchanged":
            lines.append(
                f"[{change.category.value.upper()}] {change.rule_id}: "
                f"{change.baseline.value} -> {change.current.value}"
            )
    return "\n".join(lines)


def render_comparison_markdown(report: ComparisonReport) -> str:
    lines = [
        f"# EvidenceLint comparison: `{report.current.repository}`",
        "",
        f"- Baseline SHA: `{report.baseline.default_sha}`",
        f"- Current SHA: `{report.current.default_sha}`",
        f"- Rule set: `{report.current.rule_set_version}`",
        f"- Policy digest: `{report.policy_digest}`",
        "",
        "| Category | Rule | Baseline | Current |",
        "|---|---|---|---|",
    ]
    for change in report.changes:
        if change.category.value != "unchanged":
            lines.append(
                f"| `{change.category.value}` | `{change.rule_id}` | "
                f"`{change.baseline.value}` | `{change.current.value}` |"
            )
    if all(change.category.value == "unchanged" for change in report.changes):
        lines.append("| `unchanged` | — | — | — |")
    return "\n".join(lines)
