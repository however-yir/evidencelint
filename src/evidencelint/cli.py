from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .batch import scan_owned_account
from .collector import collect_repository
from .github import GithubApiError, GithubClient, discover_token
from .reporting import (
    batch_strict_exit_code,
    render,
    render_batch,
    strict_exit_code,
)
from .rules import evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidencelint",
        description="Read-only, no-clone evidence audits for GitHub AI projects.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="audit one owner/repository target")
    scan.add_argument("repository", help="GitHub repository in owner/name form")
    scan.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="report format (default: text)",
    )
    scan.add_argument("--output", type=Path, help="write the report to this file")
    scan.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when a rule is failed or missing",
    )
    scan.add_argument(
        "--anonymous",
        action="store_true",
        help="do not discover or use a GitHub token",
    )

    batch = subparsers.add_parser(
        "batch",
        help="audit every repository owned by the authenticated account",
    )
    batch.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="report format (default: text)",
    )
    batch.add_argument("--output", type=Path, help="write the report to this file")
    batch.add_argument(
        "--workers",
        type=int,
        default=4,
        help="parallel repository scans, from 1 to 8 (default: 4)",
    )
    batch.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when collection fails or any rule is failed/missing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = None if getattr(args, "anonymous", False) else discover_token()
    if args.command == "batch" and token is None:
        print("evidencelint: batch requires GitHub authentication", file=sys.stderr)
        return 2
    client = GithubClient(token=token)
    try:
        if args.command == "scan":
            report = evaluate(collect_repository(args.repository, client))
            rendered = render(report, args.format)
            exit_code = strict_exit_code(report) if args.strict else 0
        else:
            report = scan_owned_account(client, workers=args.workers)
            rendered = render_batch(report, args.format)
            exit_code = batch_strict_exit_code(report) if args.strict else 0
    except (GithubApiError, ValueError) as exc:
        print(f"evidencelint: {exc}", file=sys.stderr)
        return 2

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {args.format} report to {args.output}")
    else:
        print(rendered)

    return exit_code
