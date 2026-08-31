from __future__ import annotations

import re
import unittest
from pathlib import Path

import evidencelint


ROOT = Path(__file__).resolve().parents[1]


class ReleaseAssetTests(unittest.TestCase):
    def test_package_versions_match_release_candidate(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)

        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "0.1.0")
        self.assertEqual(evidencelint.__version__, "0.1.0")
        self.assertIn(
            'Repository = "https://github.com/however-yir/evidencelint"',
            pyproject,
        )

    def test_public_action_preserves_no_clone_boundary(self) -> None:
        action = (ROOT / "action.yml").read_text(encoding="utf-8")

        self.assertNotIn("actions/checkout", action)
        self.assertNotIn("git clone", action.lower())
        self.assertIn('PYTHONPATH="$GITHUB_ACTION_PATH/src"', action)
        self.assertIn('scan "$repository"', action)
        self.assertIn("GITHUB_TOKEN", action)

    def test_ci_covers_supported_edges_and_clean_wheel_install(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn('python-version: ["3.9", "3.13"]', workflow)
        self.assertIn("python -m compileall -q src tests scripts", workflow)
        self.assertIn("python -m pip wheel --no-deps --wheel-dir dist .", workflow)
        self.assertIn("evidencelint==0.1.0", workflow)
        self.assertIn("uses: ./", workflow)

    def test_release_smoke_uses_published_action_without_checkout(self) -> None:
        workflow = (ROOT / ".github/workflows/release-smoke.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("uses: however-yir/evidencelint@v0.1.0", workflow)
        self.assertNotIn("actions/checkout", workflow)
        self.assertNotIn("git clone", workflow.lower())
        self.assertIn('report["schema_version"] == "evidencelint-report-v1"', workflow)

    def test_release_smoke_uploads_short_lived_report_artifact(self) -> None:
        workflow = (ROOT / ".github/workflows/release-smoke.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertIn("path: ${{ steps.audit.outputs.report }}", workflow)
        self.assertIn("retention-days: 7", workflow)

    def test_future_release_is_verified_before_least_privilege_publish(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("permissions: {}", workflow)
        self.assertIn("python scripts/release_version.py", workflow)
        self.assertIn("build==1.6.0", workflow)
        self.assertIn('python-version: ["3.9", "3.13"]', workflow)
        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertIn("uses: actions/download-artifact@v8", workflow)
        self.assertIn("if: github.ref_type == 'tag'", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("--verify-tag", workflow)
        self.assertNotIn("pypi", workflow.lower())

    def test_future_release_publishes_verified_distribution_checksums(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "sha256sum evidencelint-*.whl evidencelint-*.tar.gz > SHA256SUMS",
            workflow,
        )
        self.assertIn("sha256sum --check SHA256SUMS", workflow)
        self.assertIn("path: dist/*", workflow)

    def test_readme_exposes_release_and_copyable_action_usage(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(
            "https://github.com/however-yir/evidencelint/releases/tag/v0.1.0",
            readme,
        )
        self.assertIn("uses: however-yir/evidencelint@v0.1.0", readme)
        self.assertNotIn("actions/checkout", readme)

    def test_private_account_reports_are_excluded_from_public_release(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        local_reports = (
            "examples/however-yir-action-plan.md",
            "examples/however-yir-portfolio.json",
            "examples/however-yir-portfolio.md",
        )

        for path in local_reports:
            self.assertIn(path, ignored)
            self.assertNotIn(f"]({path})", readme)
        self.assertIn("prune examples", manifest)
        self.assertIn("include examples/ragproof-report.json", manifest)
        self.assertIn("include scripts/release_version.py", manifest)


if __name__ == "__main__":
    unittest.main()
