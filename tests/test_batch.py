from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch

from evidencelint.batch import scan_owned_account
from evidencelint.github import GithubApiError
from evidencelint.models import (
    ActionCategory,
    AuditReport,
    BatchReport,
    EvidenceStatus,
    Finding,
    RepositorySnapshot,
)
from evidencelint.reporting import render_batch


class StubClient:
    rate_limit = {"limit": 5000, "remaining": 4900, "resource": "core"}


def make_snapshot(repository: str) -> RepositorySnapshot:
    return RepositorySnapshot(
        repository=repository,
        captured_at="2026-08-31T00:00:00+00:00",
        metadata={
            "visibility": "public",
            "default_branch": "main",
            "topics": [],
            "license": {"spdx_id": "MIT"},
        },
        default_sha="a" * 40,
        check_runs=(
            {"name": "CI", "status": "completed", "conclusion": "success"},
        ),
        tree_paths=("LICENSE", "README.md", "tests/test_demo.py"),
        tree_truncated=False,
        readme="# Demo\n",
        latest_release=None,
    )


class BatchTests(unittest.TestCase):
    def test_action_queue_classifies_sorts_and_redacts(self) -> None:
        public_report = AuditReport(
            snapshot=make_snapshot("me/zeta"),
            findings=(
                Finding(
                    "docs.link",
                    "documentation",
                    EvidenceStatus.FAILED,
                    "Broken link",
                    "A linked path does not exist.",
                    ("docs/missing.md",),
                ),
                Finding(
                    "delivery.release",
                    "delivery",
                    EvidenceStatus.MISSING,
                    "Release",
                    "No release exists.",
                ),
            ),
        )
        private_snapshot = make_snapshot("me/alpha")
        private_snapshot = replace(
            private_snapshot,
            metadata={**private_snapshot.metadata, "visibility": "private"},
        )
        private_report = AuditReport(
            snapshot=private_snapshot,
            findings=(
                Finding(
                    "provenance.boundary",
                    "provenance",
                    EvidenceStatus.PARTIAL,
                    "Boundary",
                    "Boundary evidence needs review.",
                    ("private/provenance.md",),
                ),
                Finding(
                    "quality.tests",
                    "quality",
                    EvidenceStatus.UNAVAILABLE,
                    "Tests",
                    "Tree access was unavailable.",
                    ("private/tests",),
                ),
            ),
        )
        report = BatchReport(
            owner="me",
            captured_at="2026-08-31T00:00:00+00:00",
            reports=(public_report, private_report),
        )

        self.assertEqual(
            [item.category for item in report.action_items()],
            [
                ActionCategory.CONFIRMED_DEFECT,
                ActionCategory.COLLECTION_BLOCKER,
                ActionCategory.REVIEW_REQUIRED,
                ActionCategory.EVIDENCE_GAP,
            ],
        )
        payload = report.to_dict()
        private_actions = [
            item for item in payload["actions"]["items"]
            if item["visibility"] == "private"
        ]
        self.assertTrue(all(not item["evidence"] for item in private_actions))
        self.assertEqual(payload["schema_version"], "evidencelint-batch-report-v3")
        rendered = render_batch(report, "markdown")
        self.assertIn("## Action queue", rendered)
        self.assertIn("### Confirmed defects", rendered)
        self.assertIn("an expected artifact is absent, not that the project is broken", rendered)
        self.assertNotIn("private/provenance.md", rendered)

    def test_one_repository_failure_does_not_discard_other_results(self) -> None:
        def collect(repository: str, client: object) -> RepositorySnapshot:
            if repository == "me/broken":
                raise GithubApiError("repos/me/broken", 403, "forbidden")
            return make_snapshot(repository)

        with patch(
            "evidencelint.batch.collect_owned_repositories",
            return_value=("me", ("me/healthy", "me/broken")),
        ), patch("evidencelint.batch.collect_repository", side_effect=collect):
            report = scan_owned_account(StubClient(), workers=2)

        self.assertEqual([item.snapshot.repository for item in report.reports], ["me/healthy"])
        self.assertIn("me/broken", report.failures)
        self.assertEqual(report.check_run_summary()["success"], 1)
        rendered_json = render_batch(report, "json")
        self.assertIn("repositories_failed", rendered_json)
        self.assertIn('"rule_set_version": "evidencelint-rules-v2"', rendered_json)
        self.assertIn(
            "Rule set: evidencelint-rules-v2",
            render_batch(report, "text"),
        )
        self.assertIn(
            "Rule set: `evidencelint-rules-v2`",
            render_batch(report, "markdown"),
        )

    def test_workers_have_a_bounded_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 8"):
            scan_owned_account(StubClient(), workers=9)


if __name__ == "__main__":
    unittest.main()
