from __future__ import annotations

import unittest

from evidencelint.github import GithubClient


class GithubClientTests(unittest.TestCase):
    def test_concurrent_rate_limit_snapshots_keep_worst_observed_coverage(self) -> None:
        client = GithubClient()

        client._capture_rate_limit(
            {
                "X-RateLimit-Limit": "5000",
                "X-RateLimit-Remaining": "4900",
                "X-RateLimit-Used": "100",
                "X-RateLimit-Resource": "core",
                "X-RateLimit-Reset": "1788141600",
            }
        )
        client._capture_rate_limit(
            {
                "X-RateLimit-Limit": "5000",
                "X-RateLimit-Remaining": "4980",
                "X-RateLimit-Used": "20",
                "X-RateLimit-Resource": "core",
                "X-RateLimit-Reset": "1788141600",
            }
        )

        self.assertEqual(client.rate_limit["remaining"], 4900)
        self.assertEqual(client.rate_limit["used"], 100)


if __name__ == "__main__":
    unittest.main()
