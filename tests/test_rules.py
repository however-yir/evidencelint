from __future__ import annotations

import json
import unittest

from evidencelint.models import EvidenceStatus, RepositorySnapshot, RULE_SET_VERSION
from evidencelint.reporting import render, strict_exit_code
from evidencelint.rules import RULE_CONTRACTS, evaluate


def snapshot(**overrides: object) -> RepositorySnapshot:
    values: dict[str, object] = {
        "repository": "example/agent",
        "captured_at": "2026-08-31T00:00:00+00:00",
        "metadata": {
            "visibility": "public",
            "default_branch": "main",
            "fork": False,
            "archived": False,
            "language": "Python",
            "topics": ["ai-agent"],
            "license": {"spdx_id": "MIT"},
            "description": "A small AI agent tool",
        },
        "default_sha": "a" * 40,
        "check_runs": ({"name": "tests", "status": "completed", "conclusion": "success"},),
        "tree_paths": (
            ".env.example",
            ".github/workflows/ci.yml",
            "LICENSE",
            "README.md",
            "SECURITY.md",
            "docs/guide.md",
            "docs/provenance.md",
            "evaluation/cases.jsonl",
            "tests/test_core.py",
        ),
        "tree_truncated": False,
        "readme": "# Agent\nBased on an upstream project. See [guide](docs/guide.md).",
        "latest_release": {"tag_name": "v0.1.0"},
        "collection_issues": {},
    }
    values.update(overrides)
    return RepositorySnapshot(**values)  # type: ignore[arg-type]


class RuleTests(unittest.TestCase):
    def test_rule_contract_v2_is_frozen_and_every_status_is_reachable(self) -> None:
        expected = {
            "docs.readme": (
                "documentation",
                {"verified", "missing", "unavailable"},
            ),
            "delivery.license": (
                "delivery",
                {"verified", "missing", "unavailable"},
            ),
            "quality.current_ci": (
                "quality",
                {"verified", "partial", "missing", "failed", "unavailable"},
            ),
            "quality.workflows": (
                "quality",
                {"verified", "missing", "unavailable"},
            ),
            "docs.workflow_badges": (
                "documentation",
                {"verified", "failed", "unavailable", "not_applicable"},
            ),
            "quality.tests": (
                "quality",
                {"verified", "missing", "unavailable"},
            ),
            "delivery.release": (
                "delivery",
                {"verified", "missing", "unavailable"},
            ),
            "delivery.release_links": (
                "delivery",
                {"verified", "failed", "unavailable", "not_applicable"},
            ),
            "ai.evaluation_assets": (
                "ai_evidence",
                {"verified", "missing", "unavailable", "not_applicable"},
            ),
            "security.policy": (
                "security",
                {"verified", "missing", "unavailable"},
            ),
            "security.environment_template": (
                "security",
                {"verified", "missing", "unavailable"},
            ),
            "provenance.boundary": (
                "provenance",
                {"verified", "partial", "unavailable", "not_applicable"},
            ),
            "docs.internal_links": (
                "documentation",
                {"verified", "failed", "unavailable", "not_applicable"},
            ),
        }
        actual_contract = {
            contract.rule_id: (
                contract.dimension,
                {status.value for status in contract.allowed_statuses},
            )
            for contract in RULE_CONTRACTS
        }
        self.assertEqual(RULE_SET_VERSION, "evidencelint-rules-v2")
        self.assertEqual(actual_contract, expected)

        no_license = dict(snapshot().metadata)
        no_license["license"] = None
        non_ai = dict(no_license)
        non_ai.update({"topics": [], "description": "A command-line utility"})
        scenarios = (
            snapshot(),
            snapshot(
                metadata=no_license,
                check_runs=(),
                tree_paths=(),
                readme=None,
                latest_release=None,
            ),
            snapshot(
                metadata=no_license,
                check_runs=(),
                tree_paths=(),
                readme=None,
                latest_release=None,
                collection_issues={
                    "readme": "README request denied",
                    "tree": "tree request denied",
                    "check_runs": "check-run request denied",
                    "release": "release request denied",
                },
            ),
            snapshot(
                check_runs=({"name": "tests", "status": "in_progress", "conclusion": None},),
            ),
            snapshot(
                check_runs=({"name": "tests", "status": "completed", "conclusion": "failure"},),
                readme="# Agent\nSee [missing](docs/missing.md).",
            ),
            snapshot(
                readme="# Distribution\nBased on [upstream](https://github.com/example/upstream).",
                tree_paths=("README.md",),
            ),
            snapshot(
                readme="# Distribution\nBased on [upstream](https://github.com/example/upstream).",
                tree_paths=("README.md",),
                collection_issues={"tree": "tree request denied"},
            ),
            snapshot(metadata=non_ai, readme="# Command-line utility\n"),
            snapshot(
                readme=(
                    "![CI](https://github.com/example/agent/actions/workflows/"
                    "ci.yml/badge.svg?branch=main)"
                ),
                tree_paths=(".github/workflows/ci.yml", "README.md"),
            ),
            snapshot(
                readme=(
                    "![CI](https://github.com/example/agent/actions/workflows/"
                    "missing.yml/badge.svg)"
                ),
            ),
            snapshot(
                readme=(
                    "![CI](https://github.com/example/agent/actions/workflows/"
                    "ci.yml/badge.svg)"
                ),
                collection_issues={"tree": "tree request denied"},
            ),
            snapshot(
                readme=(
                    "[v0.1.0](https://github.com/example/agent/releases/tag/v0.1.0)"
                ),
                release_tags=("v0.1.0",),
            ),
            snapshot(
                readme=(
                    "[v0.1.0](https://github.com/example/agent/releases/tag/v0.1.0)"
                ),
                release_tags=(),
            ),
            snapshot(
                readme=(
                    "[v0.1.0](https://github.com/example/agent/releases/tag/v0.1.0)"
                ),
                collection_issues={"release_catalog": "release request denied"},
            ),
        )
        observed = {rule_id: set() for rule_id in expected}
        for item in scenarios:
            for finding in evaluate(item).findings:
                observed[finding.rule_id].add(finding.status.value)

        expected_statuses = {
            rule_id: statuses for rule_id, (_, statuses) in expected.items()
        }
        self.assertEqual(observed, expected_statuses)

    def test_complete_ai_project_has_no_failed_or_missing_rules(self) -> None:
        report = evaluate(snapshot())
        blocked = {EvidenceStatus.FAILED, EvidenceStatus.MISSING}
        self.assertFalse(any(item.status in blocked for item in report.findings))
        self.assertEqual(strict_exit_code(report), 0)

    def test_github_fork_metadata_verifies_provenance_without_readme_wording(self) -> None:
        metadata = dict(snapshot().metadata)
        metadata.update(
            {
                "fork": True,
                "parent": {"full_name": "example/upstream"},
            }
        )
        report = evaluate(snapshot(metadata=metadata, readme="# Distribution\n"))
        finding = next(
            item for item in report.findings if item.rule_id == "provenance.boundary"
        )
        self.assertEqual(finding.status, EvidenceStatus.VERIFIED)
        self.assertEqual(finding.evidence, ("example/upstream",))

    def test_workflow_badge_targets_current_repository_tree(self) -> None:
        report = evaluate(
            snapshot(
                readme=(
                    "![CI](https://github.com/example/agent/actions/workflows/"
                    "ci.yml/badge.svg?branch=main)\n"
                    "![Dependency](https://github.com/other/project/actions/workflows/"
                    "external.yml/badge.svg)"
                ),
                tree_paths=(".github/workflows/ci.yml", "README.md"),
            )
        )
        finding = next(
            item for item in report.findings if item.rule_id == "docs.workflow_badges"
        )
        self.assertEqual(finding.status, EvidenceStatus.VERIFIED)
        self.assertEqual(finding.evidence, (".github/workflows/ci.yml",))

    def test_missing_workflow_badge_and_release_tag_fail(self) -> None:
        report = evaluate(
            snapshot(
                readme=(
                    "![CI](https://github.com/example/agent/actions/workflows/"
                    "missing.yml/badge.svg)\n"
                    "[v9](https://github.com/example/agent/releases/tag/v9)"
                ),
                release_tags=("v0.1.0",),
            )
        )
        by_id = {finding.rule_id: finding for finding in report.findings}
        self.assertEqual(by_id["docs.workflow_badges"].status, EvidenceStatus.FAILED)
        self.assertEqual(by_id["docs.workflow_badges"].evidence, ("missing.yml",))
        self.assertEqual(by_id["delivery.release_links"].status, EvidenceStatus.FAILED)
        self.assertEqual(by_id["delivery.release_links"].evidence, ("v9",))

    def test_red_ci_and_broken_readme_link_fail(self) -> None:
        report = evaluate(
            snapshot(
                check_runs=(
                    {"name": "tests", "status": "completed", "conclusion": "failure"},
                ),
                readme="# Agent\nSee [missing](docs/missing.md).",
            )
        )
        by_id = {finding.rule_id: finding for finding in report.findings}
        self.assertEqual(by_id["quality.current_ci"].status, EvidenceStatus.FAILED)
        self.assertEqual(by_id["docs.internal_links"].status, EvidenceStatus.FAILED)
        self.assertEqual(by_id["docs.internal_links"].evidence, ("docs/missing.md",))
        self.assertEqual(strict_exit_code(report), 1)

    def test_truncated_tree_never_claims_path_absence(self) -> None:
        report = evaluate(snapshot(tree_paths=("README.md",), tree_truncated=True))
        by_id = {finding.rule_id: finding for finding in report.findings}
        for rule_id in (
            "quality.workflows",
            "quality.tests",
            "ai.evaluation_assets",
            "security.policy",
            "security.environment_template",
            "docs.internal_links",
        ):
            self.assertEqual(by_id[rule_id].status, EvidenceStatus.UNAVAILABLE)

    def test_benchmark_document_counts_as_ai_evaluation_evidence(self) -> None:
        report = evaluate(
            snapshot(
                tree_paths=(
                    "README.md",
                    "docs/BENCHMARK.md",
                    "tests/test_metrics.py",
                )
            )
        )
        by_id = {finding.rule_id: finding for finding in report.findings}
        self.assertEqual(by_id["ai.evaluation_assets"].status, EvidenceStatus.VERIFIED)
        self.assertIn("docs/BENCHMARK.md", by_id["ai.evaluation_assets"].evidence)

    def test_upstream_api_address_is_not_a_fork_relationship(self) -> None:
        report = evaluate(
            snapshot(
                readme="# Query page\n真实上游地址配置在服务端。",
                tree_paths=("README.md",),
            )
        )
        by_id = {finding.rule_id: finding for finding in report.findings}
        self.assertEqual(by_id["provenance.boundary"].status, EvidenceStatus.NOT_APPLICABLE)

    def test_framework_dependency_is_not_a_fork_relationship(self) -> None:
        report = evaluate(
            snapshot(
                readme="# Platform\nBased on Spring Boot and Spring AI.",
                tree_paths=("README.md",),
            )
        )
        by_id = {finding.rule_id: finding for finding in report.findings}
        self.assertEqual(by_id["provenance.boundary"].status, EvidenceStatus.NOT_APPLICABLE)

    def test_github_upstream_with_boundary_notice_is_verified(self) -> None:
        report = evaluate(
            snapshot(
                readme=(
                    "# Distribution\nBased on "
                    "[Upstream](https://github.com/example/upstream)."
                ),
                tree_paths=("LICENSE.HOWEVER", "README.md"),
            )
        )
        by_id = {finding.rule_id: finding for finding in report.findings}
        self.assertEqual(by_id["provenance.boundary"].status, EvidenceStatus.VERIFIED)
        self.assertIn("LICENSE.HOWEVER", by_id["provenance.boundary"].evidence)

    def test_profile_and_portfolio_are_not_ai_implementation_projects(self) -> None:
        metadata = dict(snapshot().metadata)
        metadata.update(
            {
                "topics": [],
                "description": "AI engineering portfolio",
            }
        )
        report = evaluate(
            snapshot(
                repository="example/portfolio",
                metadata=metadata,
                readme="# AI Engineering Portfolio\n",
            )
        )
        by_id = {finding.rule_id: finding for finding in report.findings}
        self.assertEqual(by_id["ai.evaluation_assets"].status, EvidenceStatus.NOT_APPLICABLE)

    def test_json_report_excludes_raw_readme(self) -> None:
        report = evaluate(snapshot(readme="# SECRET-LIKE-CONTENT\n"))
        payload = json.loads(render(report, "json"))
        self.assertNotIn("SECRET-LIKE-CONTENT", json.dumps(payload))
        self.assertEqual(payload["schema_version"], "evidencelint-report-v2")
        self.assertEqual(payload["rule_set_version"], "evidencelint-rules-v2")
        self.assertIn("Rule set: evidencelint-rules-v2", render(report, "text"))
        self.assertIn("Rule set: `evidencelint-rules-v2`", render(report, "markdown"))

    def test_private_report_redacts_evidence_paths(self) -> None:
        metadata = dict(snapshot().metadata)
        metadata["visibility"] = "private"
        report = evaluate(snapshot(metadata=metadata))

        payload = json.loads(render(report, "json"))

        self.assertTrue(all(not item["evidence"] for item in payload["findings"]))
        self.assertNotIn("docs/guide.md", render(report, "text"))


if __name__ == "__main__":
    unittest.main()
