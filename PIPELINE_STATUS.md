# EvidenceLint - Pipeline Status

Updated: 2026-08-31

## Current stage

**M5: GitHub v0.1.0 — published**

## Completed

- Concept, target users, and no-clone boundary locked.
- Six-week plan, quality gates, risks, and success criteria documented.
- Project package and command entry point defined.
- Read-only GitHub collector and versioned report schema implemented.
- Eleven deterministic rules and three output formats implemented.
- Thirty-five offline tests pass on Python 3.9 and Python 3.13.
- Live smoke checks passed against `ragproof`, `forgepilot-studio`, and an
  authorized private repository without cloning or mutation.
- Check-run and owned-repository pagination implemented beyond 100 items.
- Authenticated account-wide batch scan implemented with 1-8 bounded workers
  and isolated per-repository failures.
- Concurrent rate-limit coverage records the most conservative observed value.
- Private-repository evidence paths are redacted in every report format.
- Live baseline audit completed for all 15 owned repositories: 15 audited, 0
  collection failures, and 151/151 current default-branch checks successful.
- JSON and Markdown portfolio reports saved under `examples/`.
- Thirteen rule identifiers, dimensions, allowed statuses, and ordering are
  frozen under `evidencelint-rules-v2`.
- Runtime validation rejects undeclared rule output and every allowed status
  has an offline reachability regression.
- All report formats expose the schema and rule-set versions.
- Current-repository Actions badge targets are checked against real workflow
  paths without requesting external badge providers.
- Explicit current-repository release-tag links are checked against paginated
  published Releases; drafts do not count.
- Live M3 audit verified workflow badges in 8 repositories and the explicit
  `knowledgeops-agent` `v1.0.0` Release link with no new failures.
- Batch schema v2 provides a deterministic action queue with stable repository
  ordering and four non-overlapping action categories.
- Live portfolio result: 1 confirmed defect, 0 collection blockers, 2 review
  items, 18 evidence gaps, and 6 repositories without action items.
- Private action evidence remains redacted in JSON, text, and Markdown output.
- A fresh Python 3.9 environment successfully built and installed the wheel,
  ran the installed CLI, and completed a live `ragproof` scan.
- A curated portfolio action plan distinguishes must-fix defects from optional
  showcase improvements without inflating repository claims.
- Package and CLI versions are synchronized at `0.1.0`.
- The composite Action preserves the no-clone boundary, validates inputs, and
  passed a local equivalent live run against `ragproof`.
- Development CI covers Python 3.9 and 3.13, compilation, warning-free package
  builds, clean-wheel installation, and Action smoke verification.
- GitHub's official checkout, Python setup, and artifact upload integrations
  use their Node.js 24-compatible v7 releases.
- Warning-free wheel and source distributions were built with MIT SPDX metadata
  and `Requires-Python: >=3.9`.
- A clean environment installed only the built wheel, passed dependency checks,
  and completed a live public-repository scan.
- Local account-wide reports are ignored from version control and excluded from
  source distributions to avoid exposing private repository names.
- A manual consumer smoke workflow pins the published `v0.1.0` Action and
  performs no source checkout.
- The README links the exact GitHub Release and exposes a copyable
  least-privilege Action example.
- Release smoke retains its verified public report as a seven-day Artifact
  through the composite Action's declared output path.
- Future GitHub Releases have a manual dry-run path and a tag-only,
  least-privilege publish path with Python 3.9/3.13 candidate verification.
- Package/tag version matching is isolated in a source-distributed helper with
  offline matching and mismatch regressions.
- Future wheel and source distributions receive a published `SHA256SUMS` that
  is verified before installation on either supported Python edge.

## Publication status

The public GitHub repository, verified `v0.1.0` tag, and GitHub Release are
available at `however-yir/evidencelint`. PyPI publication was intentionally not
performed.

## Next checkpoint

Use live feedback from the GitHub Action and public users to decide whether a
v0.1.1 maintenance release or PyPI trusted publishing has measured value.

## Blockers

The portfolio audit identified one defect outside this project's scope:
`knowledgeops-agent` references the missing relative path
`docs/career/resume-upgrade-checklist.md`.
