from __future__ import annotations

import base64
import unittest
from typing import Any

from evidencelint.collector import collect_owned_repositories, collect_repository
from evidencelint.github import GithubApiError


class FakeClient:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get_json(self, path: str) -> Any:
        self.calls.append(path)
        response = self.responses.get(path)
        if isinstance(response, Exception):
            raise response
        if response is None:
            raise AssertionError(f"unexpected API path: {path}")
        return response


class CollectorTests(unittest.TestCase):
    def test_collects_remote_snapshot_without_source_checkout(self) -> None:
        readme = base64.b64encode(b"# Demo\n").decode("ascii")
        client = FakeClient(
            {
                "repos/example/demo": {
                    "default_branch": "main",
                    "visibility": "public",
                    "topics": [],
                },
                "repos/example/demo/commits/main": {
                    "sha": "abc123",
                    "commit": {"tree": {"sha": "tree123"}},
                },
                "repos/example/demo/commits/abc123/check-runs?per_page=100&page=1": {
                    "total_count": 1,
                    "check_runs": [{"name": "CI", "status": "completed", "conclusion": "success"}]
                },
                "repos/example/demo/git/trees/tree123?recursive=1": {
                    "truncated": False,
                    "tree": [
                        {"path": "README.md", "type": "blob"},
                        {"path": "src", "type": "tree"},
                        {"path": "src/demo.py", "type": "blob"},
                    ],
                },
                "repos/example/demo/readme": {"encoding": "base64", "content": readme},
                "repos/example/demo/releases/latest": GithubApiError(
                    "repos/example/demo/releases/latest", 404, "Not Found"
                ),
            }
        )

        result = collect_repository("example/demo", client)

        self.assertEqual(result.default_sha, "abc123")
        self.assertEqual(result.tree_paths, ("README.md", "src/demo.py"))
        self.assertEqual(result.readme, "# Demo\n")
        self.assertIsNone(result.latest_release)
        self.assertEqual(result.collection_issues, {})

    def test_optional_api_failure_is_recorded_as_unavailable(self) -> None:
        readme = base64.b64encode(b"# Demo\n").decode("ascii")
        client = FakeClient(
            {
                "repos/example/demo": {"default_branch": "main"},
                "repos/example/demo/commits/main": {
                    "sha": "abc123",
                    "commit": {"tree": {"sha": "tree123"}},
                },
                "repos/example/demo/commits/abc123/check-runs?per_page=100&page=1": GithubApiError(
                    "checks", 403, "rate limited"
                ),
                "repos/example/demo/git/trees/tree123?recursive=1": {
                    "truncated": False,
                    "tree": [],
                },
                "repos/example/demo/readme": {"encoding": "base64", "content": readme},
                "repos/example/demo/releases/latest": GithubApiError("release", 404, "Not Found"),
            }
        )

        result = collect_repository("example/demo", client)

        self.assertIn("check_runs", result.collection_issues)
        self.assertEqual(result.check_runs, ())

    def test_check_runs_are_paginated_past_one_hundred(self) -> None:
        readme = base64.b64encode(b"# Demo\n").decode("ascii")
        first_page = [
            {"name": f"check-{index}", "status": "completed", "conclusion": "success"}
            for index in range(100)
        ]
        client = FakeClient(
            {
                "repos/example/demo": {"default_branch": "main"},
                "repos/example/demo/commits/main": {
                    "sha": "abc123",
                    "commit": {"tree": {"sha": "tree123"}},
                },
                "repos/example/demo/commits/abc123/check-runs?per_page=100&page=1": {
                    "total_count": 101,
                    "check_runs": first_page,
                },
                "repos/example/demo/commits/abc123/check-runs?per_page=100&page=2": {
                    "total_count": 101,
                    "check_runs": [
                        {"name": "check-100", "status": "completed", "conclusion": "success"}
                    ],
                },
                "repos/example/demo/git/trees/tree123?recursive=1": {
                    "truncated": False,
                    "tree": [],
                },
                "repos/example/demo/readme": {"encoding": "base64", "content": readme},
                "repos/example/demo/releases/latest": GithubApiError("release", 404, "Not Found"),
            }
        )

        result = collect_repository("example/demo", client)

        self.assertEqual(len(result.check_runs), 101)
        self.assertIn("page=2", client.calls[3])

    def test_release_claims_collect_paginated_published_tags(self) -> None:
        readme = base64.b64encode(
            b"[release](https://github.com/example/demo/releases/tag/v100)\n"
        ).decode("ascii")
        first_page = [
            {"tag_name": f"v{index}", "draft": index == 0}
            for index in range(100)
        ]
        client = FakeClient(
            {
                "repos/example/demo": {"default_branch": "main"},
                "repos/example/demo/commits/main": {
                    "sha": "abc123",
                    "commit": {"tree": {"sha": "tree123"}},
                },
                "repos/example/demo/commits/abc123/check-runs?per_page=100&page=1": {
                    "total_count": 0,
                    "check_runs": [],
                },
                "repos/example/demo/git/trees/tree123?recursive=1": {
                    "truncated": False,
                    "tree": [{"path": "README.md", "type": "blob"}],
                },
                "repos/example/demo/readme": {"encoding": "base64", "content": readme},
                "repos/example/demo/releases/latest": {"tag_name": "v100"},
                "repos/example/demo/releases?per_page=100&page=1": first_page,
                "repos/example/demo/releases?per_page=100&page=2": [
                    {"tag_name": "v100", "draft": False}
                ],
            }
        )

        result = collect_repository("example/demo", client)

        self.assertEqual(len(result.release_tags), 100)
        self.assertNotIn("v0", result.release_tags)
        self.assertIn("v100", result.release_tags)
        self.assertIn(
            "repos/example/demo/releases?per_page=100&page=2",
            client.calls,
        )

    def test_owned_repository_inventory_is_paginated(self) -> None:
        first_page = [{"full_name": f"me/repo-{index}"} for index in range(100)]
        client = FakeClient(
            {
                "user": {"login": "me"},
                "user/repos?affiliation=owner&per_page=100&sort=updated&direction=desc&page=1": first_page,
                "user/repos?affiliation=owner&per_page=100&sort=updated&direction=desc&page=2": [
                    {"full_name": "me/repo-100"}
                ],
            }
        )

        owner, repositories = collect_owned_repositories(client)

        self.assertEqual(owner, "me")
        self.assertEqual(len(repositories), 101)
        self.assertIn("me/repo-100", repositories)
        self.assertEqual(repositories, tuple(sorted(repositories, key=str.lower)))

    def test_rejects_non_repository_target(self) -> None:
        with self.assertRaisesRegex(ValueError, "owner/name"):
            collect_repository("not-a-repository", FakeClient({}))


if __name__ == "__main__":
    unittest.main()
