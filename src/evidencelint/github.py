from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GithubApiError(RuntimeError):
    def __init__(self, path: str, status: int | None, message: str) -> None:
        self.path = path
        self.status = status
        self.message = message
        label = f"HTTP {status}" if status is not None else "network error"
        super().__init__(f"GitHub API {label} for {path}: {message}")


def discover_token() -> str | None:
    """Return an available token without ever logging it."""
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        if value := os.environ.get(name):
            return value.strip()

    if shutil.which("gh") is None:
        return None

    result = subprocess.run(
        ["gh", "auth", "token"],
        check=False,
        capture_output=True,
        text=True,
    )
    token = result.stdout.strip()
    return token or None


@dataclass
class GithubClient:
    token: str | None = None
    base_url: str = "https://api.github.com"
    timeout: float = 20.0
    rate_limit: dict[str, Any] = field(default_factory=dict, init=False)
    _rate_limit_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def get_json(self, path: str) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "evidencelint/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                self._capture_rate_limit(response.headers)
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = _error_message(exc)
            raise GithubApiError(path, exc.code, message) from exc
        except (URLError, TimeoutError) as exc:
            raise GithubApiError(path, None, str(exc.reason if isinstance(exc, URLError) else exc)) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GithubApiError(path, None, "invalid JSON response") from exc

    def _capture_rate_limit(self, headers: Any) -> None:
        values: dict[str, Any] = {}
        for header, key in (
            ("X-RateLimit-Limit", "limit"),
            ("X-RateLimit-Remaining", "remaining"),
            ("X-RateLimit-Used", "used"),
        ):
            value = headers.get(header)
            if value is not None:
                try:
                    values[key] = int(value)
                except ValueError:
                    continue
        if resource := headers.get("X-RateLimit-Resource"):
            values["resource"] = resource
        if reset := headers.get("X-RateLimit-Reset"):
            try:
                values["reset_at"] = datetime.fromtimestamp(
                    int(reset), timezone.utc
                ).isoformat()
            except ValueError:
                pass
        if values:
            with self._rate_limit_lock:
                previous = self.rate_limit
                if "limit" in previous and "limit" in values:
                    values["limit"] = max(previous["limit"], values["limit"])
                if "remaining" in previous and "remaining" in values:
                    values["remaining"] = min(
                        previous["remaining"], values["remaining"]
                    )
                if "used" in previous and "used" in values:
                    values["used"] = max(previous["used"], values["used"])
                self.rate_limit = {**previous, **values}


def _error_message(error: HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return error.reason or "request failed"
    return str(payload.get("message") or error.reason or "request failed")[:300]
