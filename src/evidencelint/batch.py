from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from .collector import JsonClient, collect_owned_repositories, collect_repository
from .github import GithubApiError
from .models import AuditReport, BatchReport
from .rules import evaluate


def scan_owned_account(client: JsonClient, *, workers: int = 4) -> BatchReport:
    if not 1 <= workers <= 8:
        raise ValueError("workers must be between 1 and 8")

    owner, repositories = collect_owned_repositories(client)
    reports_by_name: dict[str, AuditReport] = {}
    failures: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(repositories)))) as executor:
        futures = {
            executor.submit(_scan_one, repository, client): repository
            for repository in repositories
        }
        for future in as_completed(futures):
            repository = futures[future]
            try:
                reports_by_name[repository] = future.result()
            except (GithubApiError, ValueError) as exc:
                failures[repository] = str(exc)

    reports = tuple(
        reports_by_name[repository]
        for repository in repositories
        if repository in reports_by_name
    )
    return BatchReport(
        owner=owner,
        captured_at=datetime.now(timezone.utc).isoformat(),
        reports=reports,
        failures=failures,
        api_rate_limit=dict(getattr(client, "rate_limit", {})),
    )


def _scan_one(repository: str, client: JsonClient) -> AuditReport:
    return evaluate(collect_repository(repository, client))
