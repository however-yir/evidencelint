from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__
from .batch import scan_owned_account
from .comparison import compare_reports, load_report
from .collector import collect_repository
from .github import GithubApiError, GithubClient, discover_token
from .policy import apply_policy, default_policy, load_policy
from .reporting import (
    batch_strict_exit_code,
    comparison_strict_exit_code,
    render,
    render_batch,
    render_comparison,
    strict_exit_code,
)
from .rules import RULE_CONTRACTS, evaluate


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
    scan.add_argument(
        "--policy",
        type=Path,
        help="apply a transparent evidencelint-policy-v1 JSON policy",
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
    batch.add_argument(
        "--policy",
        type=Path,
        help="apply a transparent evidencelint-policy-v1 JSON policy",
    )

    compare = subparsers.add_parser(
        "compare",
        help="compare two JSON EvidenceLint reports without network access",
    )
    compare.add_argument("baseline", type=Path, help="earlier JSON report")
    compare.add_argument("current", type=Path, help="current JSON report")
    compare.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="report format (default: text)",
    )
    compare.add_argument("--output", type=Path, help="write the report to this file")
    compare.add_argument(
        "--policy",
        type=Path,
        help="apply a transparent evidencelint-policy-v1 JSON policy",
    )
    compare.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 only when the comparison identifies a new blocker",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        policy = (
            load_policy(
                args.policy,
                rule_ids=(contract.rule_id for contract in RULE_CONTRACTS),
            )
            if getattr(args, "policy", None)
            else default_policy()
        )
        if args.command == "compare":
            comparison = compare_reports(
                load_report(args.baseline),
                load_report(args.current),
                policy,
            )
            return _finish(
                render_comparison(comparison, args.format),
                args.output,
                args.format,
                comparison_strict_exit_code(comparison) if args.strict else 0,
            )

        token = None if getattr(args, "anonymous", False) else discover_token()
        if args.command == "batch" and token is None:
            print("evidencelint: batch requires GitHub authentication", file=sys.stderr)
            return 2
        client = GithubClient(token=token)
        if args.command == "scan":
            audit_report = apply_policy(
                evaluate(collect_repository(args.repository, client)), policy
            )
            return _finish(
                render(audit_report, args.format),
                args.output,
                args.format,
                strict_exit_code(audit_report) if args.strict else 0,
            )

        batch_report = scan_owned_account(client, workers=args.workers)
        policy_batch = replace(
            batch_report,
            reports=tuple(apply_policy(item, policy) for item in batch_report.reports),
        )
        return _finish(
            render_batch(policy_batch, args.format),
            args.output,
            args.format,
            batch_strict_exit_code(policy_batch) if args.strict else 0,
        )
    except (GithubApiError, ValueError) as exc:
        print(f"evidencelint: {exc}", file=sys.stderr)
        return 2


def _finish(rendered: str, output: Path | None, output_format: str, exit_code: int) -> int:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {output_format} report to {output}")
    else:
        print(rendered)
    return exit_code
