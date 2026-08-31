from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from .models import AuditReport, EvidenceStatus, Finding, RepositorySnapshot


TEST_PATH = re.compile(
    r"(^|/)(test|tests|__tests__|e2e)(/|$)|Test\.(java|kt)$|\.(spec|test)\.(js|jsx|ts|tsx)$",
    re.IGNORECASE,
)
EVALUATION_PATH = re.compile(
    r"(^|/)(eval|evals|evaluation|benchmark|benchmarks)(/|$)|"
    r"(^|/)[^/]*(eval|benchmark)[^/]*\.(md|json|jsonl|ya?ml|py)$|"
    r"(^|/)(golden|fixtures?)(/|$).*(eval|route|rag|agent)",
    re.IGNORECASE,
)
BOUNDARY_PATH = re.compile(
    r"(^|/)[^/]*(known[-_]limitations|provenance|third[-_]party|credits|notice|"
    r"upstream|fork[-_]?differentiation|license[._-]however)[^/]*$",
    re.IGNORECASE,
)
UPSTREAM_RELATION = re.compile(
    r"\b(deep fork|fork of|upstream (repo|repository|project)|upstream traceability)\b|"
    r"based on\s+\[[^\]]+\]\(https?://github\.com/|"
    r"上游(项目|仓库)|深度分叉|二次.{0,8}(开发|发行版)|衍生.{0,8}(版本|发行版)",
    re.IGNORECASE,
)
AI_TERMS = {
    "ai",
    "ai-agent",
    "agent",
    "agent-platform",
    "llm",
    "mcp",
    "rag",
    "spring-ai",
    "tool-calling",
}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
WORKFLOW_BADGE_URL = re.compile(
    r"https://github\.com/(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
    r"/actions/workflows/(?P<workflow>[^/?#\s)\"'>]+)/badge\.svg",
    re.IGNORECASE,
)
RELEASE_TAG_URL = re.compile(
    r"https://github\.com/(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
    r"/releases/tag/(?P<tag>[^/?#\s)\"'>]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RuleContract:
    rule_id: str
    dimension: str
    allowed_statuses: frozenset[EvidenceStatus]


RULE_CONTRACTS = (
    RuleContract(
        "docs.readme",
        "documentation",
        frozenset({EvidenceStatus.VERIFIED, EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE}),
    ),
    RuleContract(
        "delivery.license",
        "delivery",
        frozenset({EvidenceStatus.VERIFIED, EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE}),
    ),
    RuleContract(
        "quality.current_ci",
        "quality",
        frozenset(
            {
                EvidenceStatus.VERIFIED,
                EvidenceStatus.PARTIAL,
                EvidenceStatus.MISSING,
                EvidenceStatus.FAILED,
                EvidenceStatus.UNAVAILABLE,
            }
        ),
    ),
    RuleContract(
        "quality.workflows",
        "quality",
        frozenset({EvidenceStatus.VERIFIED, EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE}),
    ),
    RuleContract(
        "docs.workflow_badges",
        "documentation",
        frozenset(
            {
                EvidenceStatus.VERIFIED,
                EvidenceStatus.FAILED,
                EvidenceStatus.UNAVAILABLE,
                EvidenceStatus.NOT_APPLICABLE,
            }
        ),
    ),
    RuleContract(
        "quality.tests",
        "quality",
        frozenset({EvidenceStatus.VERIFIED, EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE}),
    ),
    RuleContract(
        "delivery.release",
        "delivery",
        frozenset({EvidenceStatus.VERIFIED, EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE}),
    ),
    RuleContract(
        "delivery.release_links",
        "delivery",
        frozenset(
            {
                EvidenceStatus.VERIFIED,
                EvidenceStatus.FAILED,
                EvidenceStatus.UNAVAILABLE,
                EvidenceStatus.NOT_APPLICABLE,
            }
        ),
    ),
    RuleContract(
        "ai.evaluation_assets",
        "ai_evidence",
        frozenset(
            {
                EvidenceStatus.VERIFIED,
                EvidenceStatus.MISSING,
                EvidenceStatus.UNAVAILABLE,
                EvidenceStatus.NOT_APPLICABLE,
            }
        ),
    ),
    RuleContract(
        "security.policy",
        "security",
        frozenset({EvidenceStatus.VERIFIED, EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE}),
    ),
    RuleContract(
        "security.environment_template",
        "security",
        frozenset({EvidenceStatus.VERIFIED, EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE}),
    ),
    RuleContract(
        "provenance.boundary",
        "provenance",
        frozenset(
            {
                EvidenceStatus.VERIFIED,
                EvidenceStatus.PARTIAL,
                EvidenceStatus.UNAVAILABLE,
                EvidenceStatus.NOT_APPLICABLE,
            }
        ),
    ),
    RuleContract(
        "docs.internal_links",
        "documentation",
        frozenset(
            {
                EvidenceStatus.VERIFIED,
                EvidenceStatus.FAILED,
                EvidenceStatus.UNAVAILABLE,
                EvidenceStatus.NOT_APPLICABLE,
            }
        ),
    ),
)


def evaluate(snapshot: RepositorySnapshot) -> AuditReport:
    findings = (
        _readme_rule(snapshot),
        _license_rule(snapshot),
        _current_ci_rule(snapshot),
        _workflow_rule(snapshot),
        _workflow_badge_rule(snapshot),
        _tests_rule(snapshot),
        _release_rule(snapshot),
        _release_links_rule(snapshot),
        _evaluation_rule(snapshot),
        _security_policy_rule(snapshot),
        _environment_template_rule(snapshot),
        _provenance_rule(snapshot),
        _readme_links_rule(snapshot),
    )
    _validate_findings(findings)
    return AuditReport(snapshot=snapshot, findings=findings)


def _validate_findings(findings: tuple[Finding, ...]) -> None:
    actual_ids = tuple(finding.rule_id for finding in findings)
    expected_ids = tuple(contract.rule_id for contract in RULE_CONTRACTS)
    if actual_ids != expected_ids:
        raise RuntimeError(
            "rule output does not match the versioned contract: "
            f"expected {expected_ids}, got {actual_ids}"
        )

    for finding, contract in zip(findings, RULE_CONTRACTS):
        if finding.dimension != contract.dimension:
            raise RuntimeError(
                f"{finding.rule_id} changed dimension from "
                f"{contract.dimension} to {finding.dimension}"
            )
        if finding.status not in contract.allowed_statuses:
            allowed = ", ".join(sorted(status.value for status in contract.allowed_statuses))
            raise RuntimeError(
                f"{finding.rule_id} returned unsupported status "
                f"{finding.status.value}; allowed: {allowed}"
            )


def _readme_rule(snapshot: RepositorySnapshot) -> Finding:
    if "readme" in snapshot.collection_issues:
        return _finding(
            "docs.readme",
            "documentation",
            EvidenceStatus.UNAVAILABLE,
            "README availability",
            snapshot.collection_issues["readme"],
        )
    if snapshot.readme:
        return _finding(
            "docs.readme",
            "documentation",
            EvidenceStatus.VERIFIED,
            "README availability",
            "A decodable repository README is present.",
            "README",
        )
    return _finding(
        "docs.readme",
        "documentation",
        EvidenceStatus.MISSING,
        "README availability",
        "The GitHub README endpoint returned no README.",
    )


def _license_rule(snapshot: RepositorySnapshot) -> Finding:
    license_id = ((snapshot.metadata.get("license") or {}).get("spdx_id"))
    license_paths = _matching_paths(snapshot.tree_paths, re.compile(r"(^|/)(LICENSE|COPYING)(\.|$)", re.I))
    if license_id or license_paths:
        evidence = ([f"SPDX:{license_id}"] if license_id else []) + list(license_paths[:3])
        return _finding(
            "delivery.license",
            "delivery",
            EvidenceStatus.VERIFIED,
            "License evidence",
            "GitHub metadata or the repository tree exposes license evidence.",
            *evidence,
        )
    return _path_absence(
        snapshot,
        "delivery.license",
        "delivery",
        "License evidence",
        "No license metadata or LICENSE/COPYING path was found.",
    )


def _current_ci_rule(snapshot: RepositorySnapshot) -> Finding:
    if "check_runs" in snapshot.collection_issues:
        return _finding(
            "quality.current_ci",
            "quality",
            EvidenceStatus.UNAVAILABLE,
            "Current default-branch CI",
            snapshot.collection_issues["check_runs"],
        )
    if not snapshot.check_runs:
        return _finding(
            "quality.current_ci",
            "quality",
            EvidenceStatus.MISSING,
            "Current default-branch CI",
            "The latest default-branch commit has no check runs.",
            snapshot.default_sha[:12],
        )

    pending = [run for run in snapshot.check_runs if run.get("status") != "completed"]
    accepted = {"success", "neutral", "skipped"}
    failed = [
        run
        for run in snapshot.check_runs
        if run.get("status") == "completed" and run.get("conclusion") not in accepted
    ]
    names = tuple(str(run.get("name") or "unnamed") for run in failed + pending)
    if failed:
        return _finding(
            "quality.current_ci",
            "quality",
            EvidenceStatus.FAILED,
            "Current default-branch CI",
            f"{len(failed)} failed and {len(pending)} pending check runs were observed.",
            *names[:5],
        )
    if pending:
        return _finding(
            "quality.current_ci",
            "quality",
            EvidenceStatus.PARTIAL,
            "Current default-branch CI",
            f"No failure is complete, but {len(pending)} check runs are still pending.",
            *names[:5],
        )
    return _finding(
        "quality.current_ci",
        "quality",
        EvidenceStatus.VERIFIED,
        "Current default-branch CI",
        f"All {len(snapshot.check_runs)} current check runs completed acceptably.",
        snapshot.default_sha[:12],
    )


def _workflow_rule(snapshot: RepositorySnapshot) -> Finding:
    matches = tuple(path for path in snapshot.tree_paths if path.startswith(".github/workflows/"))
    return _present_path_rule(
        snapshot,
        matches,
        "quality.workflows",
        "quality",
        "Workflow definitions",
        "No GitHub Actions workflow file was found.",
    )


def _workflow_badge_rule(snapshot: RepositorySnapshot) -> Finding:
    if "readme" in snapshot.collection_issues:
        return _finding(
            "docs.workflow_badges",
            "documentation",
            EvidenceStatus.UNAVAILABLE,
            "Workflow badge targets",
            snapshot.collection_issues["readme"],
        )
    claims = _self_workflow_badges(snapshot)
    if not claims:
        return _finding(
            "docs.workflow_badges",
            "documentation",
            EvidenceStatus.NOT_APPLICABLE,
            "Workflow badge targets",
            "No current-repository GitHub Actions badge was detected.",
        )
    if "tree" in snapshot.collection_issues:
        return _finding(
            "docs.workflow_badges",
            "documentation",
            EvidenceStatus.UNAVAILABLE,
            "Workflow badge targets",
            snapshot.collection_issues["tree"],
        )
    if snapshot.tree_truncated:
        return _finding(
            "docs.workflow_badges",
            "documentation",
            EvidenceStatus.UNAVAILABLE,
            "Workflow badge targets",
            "The recursive tree is truncated, so badge targets cannot be proved absent.",
        )

    missing = tuple(
        workflow
        for workflow in claims
        if f".github/workflows/{workflow}" not in snapshot.tree_paths
    )
    if missing:
        return _finding(
            "docs.workflow_badges",
            "documentation",
            EvidenceStatus.FAILED,
            "Workflow badge targets",
            f"{len(missing)} of {len(claims)} workflow badge targets do not exist.",
            *missing[:10],
        )
    return _finding(
        "docs.workflow_badges",
        "documentation",
        EvidenceStatus.VERIFIED,
        "Workflow badge targets",
        f"All {len(claims)} current-repository workflow badge targets exist.",
        *(f".github/workflows/{workflow}" for workflow in claims[:10]),
    )


def _tests_rule(snapshot: RepositorySnapshot) -> Finding:
    return _present_path_rule(
        snapshot,
        _matching_paths(snapshot.tree_paths, TEST_PATH),
        "quality.tests",
        "quality",
        "Test assets",
        "No conventional test path was found in the remote tree.",
    )


def _release_rule(snapshot: RepositorySnapshot) -> Finding:
    if "release" in snapshot.collection_issues:
        return _finding(
            "delivery.release",
            "delivery",
            EvidenceStatus.UNAVAILABLE,
            "Release evidence",
            snapshot.collection_issues["release"],
        )
    if snapshot.latest_release:
        return _finding(
            "delivery.release",
            "delivery",
            EvidenceStatus.VERIFIED,
            "Release evidence",
            "GitHub exposes a latest release.",
            str(snapshot.latest_release.get("tag_name") or "untagged"),
        )
    return _finding(
        "delivery.release",
        "delivery",
        EvidenceStatus.MISSING,
        "Release evidence",
        "The repository has no latest GitHub release.",
    )


def _release_links_rule(snapshot: RepositorySnapshot) -> Finding:
    if "readme" in snapshot.collection_issues:
        return _finding(
            "delivery.release_links",
            "delivery",
            EvidenceStatus.UNAVAILABLE,
            "README release links",
            snapshot.collection_issues["readme"],
        )
    claims = _self_release_tags(snapshot)
    if not claims:
        return _finding(
            "delivery.release_links",
            "delivery",
            EvidenceStatus.NOT_APPLICABLE,
            "README release links",
            "No current-repository release-tag link was detected.",
        )
    if "release_catalog" in snapshot.collection_issues:
        return _finding(
            "delivery.release_links",
            "delivery",
            EvidenceStatus.UNAVAILABLE,
            "README release links",
            snapshot.collection_issues["release_catalog"],
        )

    known_tags = set(snapshot.release_tags)
    missing = tuple(tag for tag in claims if tag not in known_tags)
    if missing:
        return _finding(
            "delivery.release_links",
            "delivery",
            EvidenceStatus.FAILED,
            "README release links",
            f"{len(missing)} of {len(claims)} linked release tags do not exist.",
            *missing[:10],
        )
    return _finding(
        "delivery.release_links",
        "delivery",
        EvidenceStatus.VERIFIED,
        "README release links",
        f"All {len(claims)} current-repository release-tag links exist.",
        *claims[:10],
    )


def _evaluation_rule(snapshot: RepositorySnapshot) -> Finding:
    if not _is_ai_project(snapshot):
        return _finding(
            "ai.evaluation_assets",
            "ai_evidence",
            EvidenceStatus.NOT_APPLICABLE,
            "AI evaluation assets",
            "Repository metadata does not identify this as an AI project.",
        )
    return _present_path_rule(
        snapshot,
        _matching_paths(snapshot.tree_paths, EVALUATION_PATH),
        "ai.evaluation_assets",
        "ai_evidence",
        "AI evaluation assets",
        "The AI project has no conventional evaluation or benchmark path.",
    )


def _security_policy_rule(snapshot: RepositorySnapshot) -> Finding:
    matches = _matching_paths(snapshot.tree_paths, re.compile(r"(^|/)SECURITY\.md$", re.I))
    return _present_path_rule(
        snapshot,
        matches,
        "security.policy",
        "security",
        "Security policy",
        "No SECURITY.md path was found.",
    )


def _environment_template_rule(snapshot: RepositorySnapshot) -> Finding:
    matches = _matching_paths(snapshot.tree_paths, re.compile(r"(^|/)\.env\.example$", re.I))
    return _present_path_rule(
        snapshot,
        matches,
        "security.environment_template",
        "security",
        "Environment template",
        "No .env.example path was found; this rule does not inspect secrets.",
    )


def _provenance_rule(snapshot: RepositorySnapshot) -> Finding:
    readme = (snapshot.readme or "").lower()
    boundary_paths = _matching_paths(snapshot.tree_paths, BOUNDARY_PATH)
    upstream_language = bool(UPSTREAM_RELATION.search(readme))
    if snapshot.metadata.get("fork"):
        parent = ((snapshot.metadata.get("parent") or {}).get("full_name"))
        return _finding(
            "provenance.boundary",
            "provenance",
            EvidenceStatus.VERIFIED,
            "Upstream boundary",
            "GitHub identifies the repository as a fork.",
            str(parent or "fork metadata"),
        )
    if not upstream_language:
        return _finding(
            "provenance.boundary",
            "provenance",
            EvidenceStatus.NOT_APPLICABLE,
            "Upstream boundary",
            "No upstream-derived positioning was detected in the README.",
        )
    if boundary_paths:
        return _finding(
            "provenance.boundary",
            "provenance",
            EvidenceStatus.VERIFIED,
            "Upstream boundary",
            "The README names an upstream relationship and boundary documentation exists.",
            *boundary_paths[:5],
        )
    return _path_absence(
        snapshot,
        "provenance.boundary",
        "provenance",
        "Upstream boundary",
        "The README names an upstream relationship, but no conventional boundary document was found.",
        partial=True,
    )


def _readme_links_rule(snapshot: RepositorySnapshot) -> Finding:
    if "readme" in snapshot.collection_issues or "tree" in snapshot.collection_issues:
        problem = snapshot.collection_issues.get("readme") or snapshot.collection_issues.get("tree")
        return _finding(
            "docs.internal_links",
            "documentation",
            EvidenceStatus.UNAVAILABLE,
            "README internal links",
            str(problem),
        )
    if not snapshot.readme:
        return _finding(
            "docs.internal_links",
            "documentation",
            EvidenceStatus.NOT_APPLICABLE,
            "README internal links",
            "There is no README to check.",
        )
    if snapshot.tree_truncated:
        return _finding(
            "docs.internal_links",
            "documentation",
            EvidenceStatus.UNAVAILABLE,
            "README internal links",
            "The recursive tree is truncated, so absent paths cannot be proved.",
        )

    candidates = _relative_markdown_links(snapshot.readme)
    broken = tuple(link for link in candidates if not _path_exists(link, snapshot.tree_paths))
    if broken:
        return _finding(
            "docs.internal_links",
            "documentation",
            EvidenceStatus.FAILED,
            "README internal links",
            f"{len(broken)} of {len(candidates)} relative README links do not resolve.",
            *broken[:10],
        )
    return _finding(
        "docs.internal_links",
        "documentation",
        EvidenceStatus.VERIFIED,
        "README internal links",
        f"All {len(candidates)} relative README links resolve in the current tree.",
    )


def _present_path_rule(
    snapshot: RepositorySnapshot,
    matches: tuple[str, ...],
    rule_id: str,
    dimension: str,
    title: str,
    missing_detail: str,
) -> Finding:
    if matches:
        return _finding(
            rule_id,
            dimension,
            EvidenceStatus.VERIFIED,
            title,
            f"Found {len(matches)} matching path(s) in the remote tree.",
            *matches[:5],
        )
    return _path_absence(snapshot, rule_id, dimension, title, missing_detail)


def _path_absence(
    snapshot: RepositorySnapshot,
    rule_id: str,
    dimension: str,
    title: str,
    missing_detail: str,
    *,
    partial: bool = False,
) -> Finding:
    if "tree" in snapshot.collection_issues:
        return _finding(
            rule_id,
            dimension,
            EvidenceStatus.UNAVAILABLE,
            title,
            snapshot.collection_issues["tree"],
        )
    if snapshot.tree_truncated:
        return _finding(
            rule_id,
            dimension,
            EvidenceStatus.UNAVAILABLE,
            title,
            "The recursive tree is truncated, so absence cannot be proved.",
        )
    return _finding(
        rule_id,
        dimension,
        EvidenceStatus.PARTIAL if partial else EvidenceStatus.MISSING,
        title,
        missing_detail,
    )


def _is_ai_project(snapshot: RepositorySnapshot) -> bool:
    """Classify whether AI-specific evidence rules should apply.

    This is a product-policy choice, not a fact supplied by GitHub. The current
    fallback is deliberately conservative and only uses explicit repository
    topics or wording near the top of the project description/README.
    """
    # TODO(maintainer): decide whether adjacent utilities such as model/API-key
    # dashboards count as AI projects even when their repository metadata does
    # not explicitly say AI, LLM, RAG, MCP, or agent.
    topics = {str(topic).lower() for topic in snapshot.metadata.get("topics") or []}
    if topics & AI_TERMS:
        return True
    description = str(snapshot.metadata.get("description") or "").lower()
    first_readme_chunk = (snapshot.readme or "")[:4000].lower()
    repository_name = snapshot.repository.rsplit("/", 1)[-1].lower()
    owner_name = snapshot.repository.split("/", 1)[0].lower()
    presentation_terms = ("portfolio", "作品集", "personal profile", "个人主页")
    if repository_name == owner_name or any(
        term in description or term in first_readme_chunk
        for term in presentation_terms
    ):
        return False
    return bool(re.search(r"\b(ai|llm|rag|agent|model context protocol)\b", description + " " + first_readme_chunk))


def _matching_paths(paths: Iterable[str], pattern: re.Pattern[str]) -> tuple[str, ...]:
    return tuple(path for path in paths if pattern.search(path))


def _relative_markdown_links(readme: str) -> tuple[str, ...]:
    links: list[str] = []
    for raw in MARKDOWN_LINK.findall(readme):
        target = raw.strip().split(" ", 1)[0].strip("<>")
        if not target or target.startswith(("#", "mailto:", "http://", "https://", "//")):
            continue
        path = unquote(urlsplit(target).path)
        normalized = posixpath.normpath(path.removeprefix("./"))
        if normalized and normalized != ".":
            links.append(normalized)
    return tuple(dict.fromkeys(links))


def _path_exists(target: str, tree_paths: tuple[str, ...]) -> bool:
    if target.startswith("../"):
        return False
    return target in tree_paths or any(path.startswith(f"{target.rstrip('/')}/") for path in tree_paths)


def _self_workflow_badges(snapshot: RepositorySnapshot) -> tuple[str, ...]:
    repository = snapshot.repository.lower()
    workflows = (
        unquote(match.group("workflow"))
        for match in WORKFLOW_BADGE_URL.finditer(snapshot.readme or "")
        if match.group("repository").lower() == repository
    )
    return tuple(dict.fromkeys(workflows))


def _self_release_tags(snapshot: RepositorySnapshot) -> tuple[str, ...]:
    repository = snapshot.repository.lower()
    tags = (
        unquote(match.group("tag"))
        for match in RELEASE_TAG_URL.finditer(snapshot.readme or "")
        if match.group("repository").lower() == repository
    )
    return tuple(dict.fromkeys(tags))


def _finding(
    rule_id: str,
    dimension: str,
    status: EvidenceStatus,
    title: str,
    detail: str,
    *evidence: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        dimension=dimension,
        status=status,
        title=title,
        detail=detail,
        evidence=tuple(item for item in evidence if item),
    )
