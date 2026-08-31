from __future__ import annotations

import unittest
from pathlib import Path

from scripts.release_version import resolve_version


ROOT = Path(__file__).resolve().parents[1]


class ReleaseVersionTests(unittest.TestCase):
    def test_branch_and_matching_tag_use_the_package_version(self) -> None:
        pyproject = ROOT / "pyproject.toml"

        self.assertEqual(resolve_version(pyproject, "branch", "main"), "0.1.0")
        self.assertEqual(resolve_version(pyproject, "tag", "v0.1.0"), "0.1.0")

    def test_mismatched_tag_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "v0.1.1 does not match v0.1.0"):
            resolve_version(ROOT / "pyproject.toml", "tag", "v0.1.1")


if __name__ == "__main__":
    unittest.main()
