from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evidencelint.comparison import ChangeCategory, compare_reports, load_report
from evidencelint.policy import default_policy
from evidencelint.reporting import comparison_strict_exit_code, render_comparison


def report_payload(*, repository: str = "example/demo", status: str = "verified") -> dict[str, object]:
    return {
        "schema_version": "evidencelint-report-v2",
        "rule_set_version": "evidencelint-rules-v2",
        "snapshot": {
            "repository": repository,
            "captured_at": "2026-08-31T00:00:00+00:00",
            "default_sha": "a" * 40,
        },
        "findings": [
            {"rule_id": "quality.tests", "status": status},
            {"rule_id": "security.policy", "status": "verified"},
        ],
    }


class ComparisonTests(unittest.TestCase):
    def test_new_blocker_is_strict_but_existing_blocker_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            current_path = Path(directory) / "current.json"
            baseline_path.write_text(json.dumps(report_payload()), encoding="utf-8")
            current_path.write_text(
                json.dumps(report_payload(status="missing")), encoding="utf-8"
            )
            comparison = compare_reports(
                load_report(baseline_path), load_report(current_path), default_policy()
            )

        self.assertEqual(comparison.changes[0].category, ChangeCategory.NEW_BLOCKER)
        self.assertEqual(comparison_strict_exit_code(comparison), 1)
        self.assertIn("new_blocker", render_comparison(comparison, "markdown"))

    def test_resolved_and_unchanged_findings_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            current_path = Path(directory) / "current.json"
            baseline_path.write_text(
                json.dumps(report_payload(status="failed")), encoding="utf-8"
            )
            current_path.write_text(json.dumps(report_payload()), encoding="utf-8")
            comparison = compare_reports(
                load_report(baseline_path), load_report(current_path), default_policy()
            )

        self.assertEqual(
            [change.category for change in comparison.changes],
            [ChangeCategory.RESOLVED_BLOCKER, ChangeCategory.UNCHANGED],
        )
        self.assertEqual(comparison_strict_exit_code(comparison), 0)

    def test_reports_must_match_repository_rule_set_and_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            current_path = Path(directory) / "current.json"
            baseline_path.write_text(json.dumps(report_payload()), encoding="utf-8")
            current_path.write_text(
                json.dumps(report_payload(repository="other/demo")), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "same repository"):
                compare_reports(
                    load_report(baseline_path), load_report(current_path), default_policy()
                )

    def test_malformed_duplicate_and_unknown_status_reports_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                load_report(path)

            payload = report_payload()
            payload["findings"] = [
                {"rule_id": "quality.tests", "status": "verified"},
                {"rule_id": "quality.tests", "status": "unknown"},
            ]
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate rule_id"):
                load_report(path)

    def test_existing_blocker_is_not_a_new_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            current_path = Path(directory) / "current.json"
            baseline_path.write_text(
                json.dumps(report_payload(status="missing")), encoding="utf-8"
            )
            current_path.write_text(
                json.dumps(report_payload(status="missing")), encoding="utf-8"
            )
            comparison = compare_reports(
                load_report(baseline_path), load_report(current_path), default_policy()
            )

        self.assertEqual(comparison.changes[0].category, ChangeCategory.UNCHANGED)
        self.assertEqual(comparison_strict_exit_code(comparison), 0)

    def test_unavailable_transition_is_changed_not_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            current_path = Path(directory) / "current.json"
            baseline_path.write_text(json.dumps(report_payload()), encoding="utf-8")
            current_path.write_text(
                json.dumps(report_payload(status="unavailable")), encoding="utf-8"
            )
            comparison = compare_reports(
                load_report(baseline_path), load_report(current_path), default_policy()
            )

        self.assertEqual(comparison.changes[0].category, ChangeCategory.CHANGED)
        self.assertEqual(comparison_strict_exit_code(comparison), 0)

    def test_rule_set_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            current_path = Path(directory) / "current.json"
            baseline_path.write_text(json.dumps(report_payload()), encoding="utf-8")
            current = report_payload()
            current["rule_set_version"] = "other"
            current_path.write_text(json.dumps(current), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "same rule_set_version"):
                compare_reports(
                    load_report(baseline_path), load_report(current_path), default_policy()
                )

    def test_v1_report_remains_a_valid_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            payload = report_payload()
            payload["schema_version"] = "evidencelint-report-v1"
            path.write_text(json.dumps(payload), encoding="utf-8")

            self.assertEqual(load_report(path).repository, "example/demo")


if __name__ == "__main__":
    unittest.main()
