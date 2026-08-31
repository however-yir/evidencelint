# EvidenceLint

[![CI](https://github.com/however-yir/evidencelint/actions/workflows/ci.yml/badge.svg)](https://github.com/however-yir/evidencelint/actions/workflows/ci.yml)

EvidenceLint is a no-clone, read-only CLI for collecting and checking the
engineering evidence that a GitHub AI project exposes today.

It answers narrow, reproducible questions:

- Is the latest default-branch commit currently green?
- Do the repository tree and metadata contain tests, evaluation assets,
  security guidance, provenance boundaries, and a release?
- Do relative links in the README resolve to real repository paths?
- Which conclusions are verified, partial, missing, failed, or unavailable?

EvidenceLint does **not** clone the repository, execute project code, mutate
GitHub, infer code originality, or turn weak signals into a fake precision
score.

## Current milestone

[v0.2.0](https://github.com/however-yir/evidencelint/releases/tag/v0.2.0) adds
transparent policy evaluation and offline report comparison. The current
pipeline supports both one repository and every repository owned by the
authenticated account:

```text
GitHub REST API -> evidence snapshot -> deterministic checks
                -> single or portfolio text/JSON/Markdown report
```

Collection paginates repository inventories and check runs, records rate-limit
coverage, isolates per-repository failures, and redacts evidence paths from
private-repository reports.

All 13 rules belong to the versioned `evidencelint-rules-v2` contract. Runtime
validation rejects accidental rule renames, dimension changes, and undeclared
statuses; regression fixtures prove that every declared status is reachable.
V2 verifies current-repository GitHub Actions badge targets against the Git
tree and README release-tag links against paginated published Releases.
Batch schema v3 adds a deterministic action queue that separates confirmed
defects, collection blockers, review items, and evidence gaps without producing
a subjective composite score.

## Installation

Install the wheel attached to the GitHub Release:

```bash
python3 -m pip install \
  https://github.com/however-yir/evidencelint/releases/download/v0.2.0/evidencelint-0.2.0-py3-none-any.whl
evidencelint --version
```

Or install from a local source directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/evidencelint --version
```

The package has not been published to PyPI. `pip install evidencelint==0.2.0`
is therefore intentionally unsupported for this release.

## Try it

```bash
evidencelint scan however-yir/ragproof
evidencelint scan however-yir/ragproof --format json
evidencelint scan however-yir/ragproof --output evidence.json
evidencelint batch --format markdown --output portfolio.md
evidencelint compare baseline.json current.json --strict
```

Authentication is optional for public repositories. EvidenceLint checks
`GITHUB_TOKEN`, then `GH_TOKEN`, then the locally authenticated GitHub CLI. It
never includes the token in a report.

The `batch` command requires authentication because it discovers the current
account and all repositories owned by it, including authorized private
repositories. It uses four workers by default; `--workers` accepts 1 through 8.
Use `--strict` when missing evidence, failed rules, or collection failures
should produce a non-zero exit status.

## Policy and comparison

A Policy can make a rule advisory without hiding its Finding. This keeps
project-specific decisions separate from collected evidence. `compare` reads
two local JSON reports without network access and exits non-zero only for a new
Policy blocker when used with `--strict`. See [docs/policy.md](docs/policy.md)
and [docs/comparison.md](docs/comparison.md).

## GitHub Action

The included composite Action audits through the GitHub API and does not
checkout the target repository:

```yaml
permissions:
  contents: read
  checks: read

jobs:
  evidence-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: however-yir/evidencelint@v0.2.0
        with:
          token: ${{ github.token }}
```

See [docs/github-action.md](docs/github-action.md) for report upload, scheduled
runs, target selection, and strict mode.

## Reproducible examples

- [Single-repository JSON report](examples/ragproof-report.json)

Account-wide portfolio reports are kept local and ignored by version control.
Even when evidence paths are redacted, those reports can reveal private
repository names and aggregate metadata and should not be published by default.

## Status semantics

| Status | Meaning |
|---|---|
| `verified` | The current API snapshot directly supports the check. |
| `partial` | Some supporting evidence exists, but the check is incomplete. |
| `missing` | The requested evidence was not present in the covered snapshot. |
| `failed` | Current evidence contradicts the expected condition. |
| `unavailable` | Permission, API, network, or truncation prevented a conclusion. |
| `not_applicable` | The rule does not apply to this repository. |

## Scope fence

v0.2.0 stays read-only and remote. Cloning, runtime execution, automatic fixes,
subjective originality scores, hosted dashboards, and GitHub mutations are on
the explicit not-yet list.

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for milestones and
[PIPELINE_STATUS.md](PIPELINE_STATUS.md) for current progress. The public rule
contract is documented in [RULES.md](RULES.md), broader product limits in
[LIMITATIONS.md](LIMITATIONS.md), and remaining remote publication work in
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). Release highlights are in
[RELEASE_NOTES.md](RELEASE_NOTES.md).
