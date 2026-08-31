from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import quote

from .github import GithubApiError
from .models import RepositorySnapshot


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class JsonClient(Protocol):
    def get_json(self, path: str) -> Any: ...


def collect_repository(repository: str, client: JsonClient) -> RepositorySnapshot:
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("repository must use the owner/name form")

    metadata = client.get_json(f"repos/{repository}")
    default_branch = metadata.get("default_branch")
    if not default_branch:
        raise ValueError("repository does not expose a default branch")

    branch_ref = quote(str(default_branch), safe="")
    commit = client.get_json(f"repos/{repository}/commits/{branch_ref}")
    default_sha = str(commit.get("sha") or "")
    if not default_sha:
        raise ValueError("default-branch commit did not include a SHA")

    issues: dict[str, str] = {}
    check_runs: tuple[dict[str, Any], ...] = ()
    try:
        check_runs = _collect_check_runs(repository, default_sha, client)
    except GithubApiError as exc:
        issues["check_runs"] = str(exc)

    tree_paths: tuple[str, ...] = ()
    tree_truncated = False
    tree_sha = ((commit.get("commit") or {}).get("tree") or {}).get("sha")
    if not tree_sha:
        issues["tree"] = "default commit did not expose a tree SHA"
    else:
        try:
            tree_payload = client.get_json(
                f"repos/{repository}/git/trees/{tree_sha}?recursive=1"
            )
            tree_paths = tuple(
                sorted(
                    str(item["path"])
                    for item in tree_payload.get("tree") or []
                    if item.get("type") == "blob" and item.get("path")
                )
            )
            tree_truncated = bool(tree_payload.get("truncated"))
        except GithubApiError as exc:
            issues["tree"] = str(exc)

    readme: str | None = None
    try:
        readme_payload = client.get_json(f"repos/{repository}/readme")
        readme = _decode_readme(readme_payload)
    except GithubApiError as exc:
        if exc.status != 404:
            issues["readme"] = str(exc)
    except (ValueError, UnicodeDecodeError) as exc:
        issues["readme"] = f"README could not be decoded: {exc}"

    latest_release: dict[str, Any] | None = None
    try:
        latest_release = client.get_json(f"repos/{repository}/releases/latest")
    except GithubApiError as exc:
        if exc.status != 404:
            issues["release"] = str(exc)

    release_tags: tuple[str, ...] = ()
    if readme and "/releases/tag/" in readme.lower():
        try:
            release_tags = _collect_release_tags(repository, client)
        except (GithubApiError, ValueError) as exc:
            issues["release_catalog"] = str(exc)

    return RepositorySnapshot(
        repository=repository,
        captured_at=datetime.now(timezone.utc).isoformat(),
        metadata=metadata,
        default_sha=default_sha,
        check_runs=check_runs,
        tree_paths=tree_paths,
        tree_truncated=tree_truncated,
        readme=readme,
        latest_release=latest_release,
        release_tags=release_tags,
        collection_issues=issues,
        api_rate_limit=dict(getattr(client, "rate_limit", {})),
    )


def collect_owned_repositories(client: JsonClient) -> tuple[str, tuple[str, ...]]:
    """Return the authenticated login and every repository it owns."""
    identity = client.get_json("user")
    owner = str(identity.get("login") or "")
    if not owner:
        raise ValueError("authenticated GitHub identity did not include a login")

    repositories: list[str] = []
    for page in range(1, 101):
        payload = client.get_json(
            "user/repos?affiliation=owner&per_page=100&sort=updated"
            f"&direction=desc&page={page}"
        )
        if not isinstance(payload, list):
            raise ValueError("owned repository inventory was not a JSON list")
        repositories.extend(
            str(item["full_name"])
            for item in payload
            if item.get("full_name")
        )
        if len(payload) < 100:
            unique = dict.fromkeys(repositories)
            return owner, tuple(sorted(unique, key=str.lower))
    raise ValueError("owned repository inventory exceeded 10,000 repositories")


def _collect_check_runs(
    repository: str,
    default_sha: str,
    client: JsonClient,
) -> tuple[dict[str, Any], ...]:
    check_runs: list[dict[str, Any]] = []
    for page in range(1, 101):
        payload = client.get_json(
            f"repos/{repository}/commits/{default_sha}/check-runs"
            f"?per_page=100&page={page}"
        )
        page_runs = payload.get("check_runs") or []
        if not isinstance(page_runs, list):
            raise ValueError("check-runs payload did not contain a JSON list")
        check_runs.extend(page_runs)
        total_count = int(payload.get("total_count") or len(check_runs))
        if len(check_runs) >= total_count or len(page_runs) < 100:
            return tuple(check_runs)
    raise ValueError("check-runs pagination exceeded 10,000 records")


def _collect_release_tags(
    repository: str,
    client: JsonClient,
) -> tuple[str, ...]:
    tags: list[str] = []
    for page in range(1, 101):
        payload = client.get_json(
            f"repos/{repository}/releases?per_page=100&page={page}"
        )
        if not isinstance(payload, list):
            raise ValueError("releases payload was not a JSON list")
        tags.extend(
            str(item["tag_name"])
            for item in payload
            if item.get("tag_name") and not item.get("draft")
        )
        if len(payload) < 100:
            return tuple(dict.fromkeys(tags))
    raise ValueError("release pagination exceeded 10,000 records")


def _decode_readme(payload: dict[str, Any]) -> str:
    if payload.get("encoding") != "base64" or not payload.get("content"):
        raise ValueError("unsupported README encoding")
    raw = base64.b64decode(str(payload["content"]), validate=False)
    return raw.decode("utf-8")
