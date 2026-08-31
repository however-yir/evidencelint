# Changelog

## Unreleased

- Add a manual consumer smoke workflow that runs the published
  `however-yir/evidencelint@v0.1.0` Action without checking out source code.
- Add regression coverage for the pinned Release smoke path, bringing the
  offline suite to 29 tests.
- Add an explicit `v0.1.0` Release link and a copyable least-privilege Action
  example to the README.
- Add regression coverage for the public README usage contract, bringing the
  offline suite to 30 tests.
- Retain the verified public Release-smoke report as a seven-day GitHub Actions
  artifact using the Action's declared report output.
- Add regression coverage for the Artifact delivery contract, bringing the
  offline suite to 31 tests.
- Add a least-privilege future-Release workflow with manual dry runs, exact
  tag/package version validation, Python 3.9/3.13 wheel verification, and
  tag-only GitHub Release creation.
- Add regression coverage for the future-Release contract, bringing the
  offline suite to 32 tests.
- Extract tag/package version matching into a directly testable release helper
  and include that helper in source distributions.
- Add matching-tag and mismatched-tag regressions, bringing the offline suite
  to 34 tests.
- Generate `SHA256SUMS` for future wheel and source distributions, verify it
  before candidate installation, and publish it with tag-created Releases.
- Add regression coverage for checksum delivery, bringing the offline suite
  to 35 tests.

## 0.1.0 - 2026-08-31

- Add the first `scan` vertical slice for read-only GitHub evidence collection.
- Add text, JSON, and Markdown report formats.
- Add deterministic checks for current CI, tests, workflows, releases,
  evaluation assets, security files, provenance, and README links.
- Add explicit unavailable handling for API failures and truncated Git trees.
- Add offline regression tests and live public-repository smoke verification.
- Add an authenticated `batch` command for every repository owned by the
  current account, with bounded parallelism and per-repository failure
  isolation.
- Paginate owned-repository discovery and current check runs beyond the first
  100 results.
- Record the most conservative observed GitHub rate-limit snapshot during
  concurrent collection.
- Redact evidence paths from private-repository JSON, text, and Markdown
  reports.
- Add portfolio-level CI and finding summaries plus strict exit behavior.
- Dogfood the collector against all 15 `however-yir` repositories without
  cloning; preserve the JSON and Markdown reports as examples.
- Expand the offline regression suite to 18 tests.
- Freeze 11 rule identifiers, dimensions, and allowed statuses as
  `evidencelint-rules-v1`.
- Include the rule-set version in every JSON, text, and Markdown report.
- Add runtime contract validation so rule drift fails immediately.
- Add a reachability regression matrix for every status declared by every
  rule, bringing the offline suite to 20 tests.
- Document rule semantics and heuristic limits in `RULES.md`.
- Add paginated published-Release tag collection when a README makes an
  explicit release-tag claim; exclude draft releases.
- Add `docs.workflow_badges` to verify current-repository Actions badge targets
  against `.github/workflows/` paths.
- Add `delivery.release_links` to verify current-repository release-tag links
  against published GitHub Releases.
- Upgrade the public contract to `evidencelint-rules-v2` with 13 rules.
- Expand the offline regression suite to 23 tests and verify the two new rules
  against all 15 owned repositories.
- Upgrade portfolio output to `evidencelint-batch-report-v2` with a stable,
  deterministic action queue.
- Separate confirmed defects, collection blockers, review items, and evidence
  gaps instead of assigning a composite score.
- Sort repositories and action items deterministically for reviewable diffs.
- Include repository-level action coverage and private-safe action evidence.
- Verify wheel build, clean installation, CLI execution, and a live public scan
  in a fresh Python 3.9 virtual environment.
- Add an evidence-based action plan for the current 15-repository portfolio and
  expand the offline suite to 24 tests.
- Prepare package and CLI version `0.1.0` as a local release candidate.
- Add a composite no-clone GitHub Action with validated inputs, read-only token
  handling, strict mode, and a report-path output.
- Add Python 3.9/3.13 development CI, clean-wheel installation, and local
  Action smoke jobs.
- Add release-asset and publication-privacy regression tests, bringing the
  offline suite to 28 tests.
- Add honest local installation, Action, product-limit, and remote-publication
  guidance without claiming an unpublished repository or package.
- Build warning-free wheel and source distributions, then verify the wheel in
  clean Python 3.9 and Python 3.13 test paths.
- Use the Node.js 24-compatible v7 releases of GitHub's official checkout,
  Python setup, and artifact upload Actions.
