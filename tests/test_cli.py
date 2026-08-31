from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evidencelint.cli import main


def report_payload(status: str) -> dict[str, object]:
    return {
        "schema_version": "evidencelint-report-v2",
        "rule_set_version": "evidencelint-rules-v2",
        "snapshot": {
            "repository": "example/demo",
            "captured_at": "2026-08-31T00:00:00+00:00",
            "default_sha": "a" * 40,
        },
        "findings": [{"rule_id": "quality.tests", "status": status}],
    }


class CliTests(unittest.TestCase):
    def test_compare_writes_report_and_returns_new_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            current = Path(directory) / "current.json"
            output = Path(directory) / "comparison.json"
            baseline.write_text(json.dumps(report_payload("verified")), encoding="utf-8")
            current.write_text(json.dumps(report_payload("missing")), encoding="utf-8")

            result = main(
                ["compare", str(baseline), str(current), "--format", "json", "--output", str(output), "--strict"]
            )

            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["summary"]["new_blocker"], 1)

    def test_compare_does_not_discover_a_github_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            current = Path(directory) / "current.json"
            baseline.write_text(json.dumps(report_payload("verified")), encoding="utf-8")
            current.write_text(json.dumps(report_payload("verified")), encoding="utf-8")
            with patch("evidencelint.cli.discover_token") as discover:
                result = main(["compare", str(baseline), str(current)])

        self.assertEqual(result, 0)
        discover.assert_not_called()

    def test_compare_invalid_report_returns_operational_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            current = Path(directory) / "current.json"
            baseline.write_text("{", encoding="utf-8")
            current.write_text(json.dumps(report_payload("verified")), encoding="utf-8")

            self.assertEqual(main(["compare", str(baseline), str(current)]), 2)

    def test_compare_policy_path_must_be_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            current = Path(directory) / "current.json"
            baseline.write_text(json.dumps(report_payload("verified")), encoding="utf-8")
            current.write_text(json.dumps(report_payload("verified")), encoding="utf-8")

            self.assertEqual(
                main(["compare", str(baseline), str(current), "--policy", str(Path(directory) / "none.json")]),
                2,
            )


if __name__ == "__main__":
    unittest.main()
