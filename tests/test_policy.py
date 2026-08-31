from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evidencelint.models import AuditReport, EvidenceStatus, Finding, RepositorySnapshot
from evidencelint.policy import apply_policy, default_policy, load_policy
from evidencelint.reporting import strict_exit_code


def make_report() -> AuditReport:
    snapshot = RepositorySnapshot(
        repository="example/demo",
        captured_at="2026-08-31T00:00:00+00:00",
        metadata={"visibility": "public", "default_branch": "main"},
        default_sha="a" * 40,
        check_runs=(),
        tree_paths=(),
        tree_truncated=False,
        readme="# Demo\n",
        latest_release=None,
    )
    return AuditReport(
        snapshot=snapshot,
        findings=(
            Finding("quality.tests", "quality", EvidenceStatus.MISSING, "Tests", "Missing."),
            Finding(
                "security.environment_template",
                "security",
                EvidenceStatus.MISSING,
                "Environment template",
                "Missing.",
            ),
        ),
    )


class PolicyTests(unittest.TestCase):
    def test_default_policy_preserves_existing_strict_behavior(self) -> None:
        report = apply_policy(make_report(), default_policy())

        self.assertEqual(report.policy.blocking_rule_ids, ("quality.tests", "security.environment_template"))
        self.assertEqual(strict_exit_code(report), 1)

    def test_advisory_rule_remains_visible_but_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "evidencelint-policy-v1",
                        "rules": {
                            "security.environment_template": {
                                "level": "advisory",
                                "reason": "Optional token only.",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = apply_policy(
                make_report(),
                load_policy(
                    path,
                    rule_ids=("quality.tests", "security.environment_template"),
                ),
            )

        self.assertEqual(report.policy.advisory_rules, ("security.environment_template",))
        self.assertEqual(report.policy.blocking_rule_ids, ("quality.tests",))
        self.assertEqual(report.to_dict()["findings"][1]["status"], "missing")
        self.assertEqual(strict_exit_code(report), 1)

    def test_advisory_reason_and_known_rule_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                '{"schema_version":"evidencelint-policy-v1","rules":{"unknown":{"level":"advisory","reason":"x"}}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unknown rule"):
                load_policy(path, rule_ids=("quality.tests",))

            path.write_text(
                '{"schema_version":"evidencelint-policy-v1","rules":{"quality.tests":{"level":"advisory"}}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "needs a reason"):
                load_policy(path, rule_ids=("quality.tests",))

    def test_duplicate_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                '{"schema_version":"evidencelint-policy-v1","rules":{},"rules":{}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate key"):
                load_policy(path, rule_ids=("quality.tests",))

    def test_required_rule_cannot_carry_an_advisory_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                '{"schema_version":"evidencelint-policy-v1","rules":{"quality.tests":{"level":"required","reason":"x"}}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must not include a reason"):
                load_policy(path, rule_ids=("quality.tests",))

    def test_invalid_schema_and_level_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                '{"schema_version":"other","rules":{}}', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "schema_version"):
                load_policy(path, rule_ids=("quality.tests",))
            path.write_text(
                '{"schema_version":"evidencelint-policy-v1","rules":{"quality.tests":{"level":"hidden"}}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "required or advisory"):
                load_policy(path, rule_ids=("quality.tests",))

    def test_all_advisory_missing_findings_do_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "evidencelint-policy-v1",
                        "rules": {
                            "quality.tests": {"level": "advisory", "reason": "Demo."},
                            "security.environment_template": {
                                "level": "advisory",
                                "reason": "Optional token.",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            policy = load_policy(
                path,
                rule_ids=("quality.tests", "security.environment_template"),
            )

        self.assertEqual(strict_exit_code(apply_policy(make_report(), policy)), 0)

    def test_equivalent_policy_content_has_a_stable_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                '{"rules":{"quality.tests":{"reason":"Demo.","level":"advisory"}},"schema_version":"evidencelint-policy-v1"}',
                encoding="utf-8",
            )
            first = load_policy(path, rule_ids=("quality.tests",))
            path.write_text(
                '{"schema_version":"evidencelint-policy-v1","rules":{"quality.tests":{"level":"advisory","reason":"Demo."}}}',
                encoding="utf-8",
            )
            second = load_policy(path, rule_ids=("quality.tests",))

        self.assertEqual(first.digest, second.digest)


if __name__ == "__main__":
    unittest.main()
