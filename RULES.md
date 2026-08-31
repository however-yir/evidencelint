# EvidenceLint rule contract

Rule set: `evidencelint-rules-v2`

This file describes the public behavior of the deterministic rule layer. A
breaking rule rename, dimension change, reordered contract, or status-semantic
change requires a new rule-set version. Adding detail or improving detection
without changing the declared meaning remains compatible.

## Status semantics

| Status | Contract meaning |
|---|---|
| `verified` | The captured API evidence directly satisfies the rule. |
| `partial` | Relevant evidence exists, but the expected boundary is incomplete. |
| `missing` | Covered evidence was collected and the expected artifact was absent. |
| `failed` | Collected evidence directly contradicts the expected condition. |
| `unavailable` | API failure, permission denial, or tree truncation prevents a conclusion. |
| `not_applicable` | Repository evidence places the rule outside its intended scope. |

`--strict` exits non-zero for `missing` and `failed`. Account-wide collection
failures also exit non-zero. `partial`, `unavailable`, and `not_applicable`
remain visible but do not currently change the strict exit code.

## Rules

| Rule ID | Dimension | Allowed statuses | Evidence boundary |
|---|---|---|---|
| `docs.readme` | documentation | verified, missing, unavailable | GitHub README endpoint |
| `delivery.license` | delivery | verified, missing, unavailable | SPDX metadata or LICENSE/COPYING path |
| `quality.current_ci` | quality | verified, partial, missing, failed, unavailable | Check runs on the captured default-branch SHA |
| `quality.workflows` | quality | verified, missing, unavailable | `.github/workflows/` tree paths |
| `docs.workflow_badges` | documentation | verified, failed, unavailable, not_applicable | Current-repository Actions badge URLs resolved against workflow paths |
| `quality.tests` | quality | verified, missing, unavailable | Conventional test paths and filenames |
| `delivery.release` | delivery | verified, missing, unavailable | Latest GitHub release endpoint |
| `delivery.release_links` | delivery | verified, failed, unavailable, not_applicable | Current-repository release-tag URLs resolved against published Releases |
| `ai.evaluation_assets` | ai_evidence | verified, missing, unavailable, not_applicable | AI classification plus conventional eval/benchmark paths |
| `security.policy` | security | verified, missing, unavailable | `SECURITY.md` tree path |
| `security.environment_template` | security | verified, missing, unavailable | `.env.example` tree path; contents are not inspected |
| `provenance.boundary` | provenance | verified, partial, unavailable, not_applicable | Fork metadata or explicit upstream wording plus boundary document |
| `docs.internal_links` | documentation | verified, failed, unavailable, not_applicable | Relative Markdown links resolved against the current tree |

## Deliberate limits

- A present path proves that an artifact is exposed, not that its contents are
  correct or high quality.
- Neutral and skipped check runs are accepted; an in-progress run is `partial`.
- AI-project classification uses explicit topics and conservative README or
  description terms. Portfolios and owner profile repositories are excluded
  unless explicit AI topics override the presentation signal.
- Framework usage such as "based on Spring AI" is not an upstream-project
  relationship. Explicit fork or upstream-repository wording is required.
- README link checking covers relative Markdown links. External URLs and
  rendered anchors remain outside v2.
- Workflow badge checking only treats `github.com/<current-repo>/actions/`
  badge URLs as claims. Badges for dependencies or unrelated repositories are
  deliberately ignored.
- Release-link checking only validates explicit
  `github.com/<current-repo>/releases/tag/<tag>` URLs. A generic Releases page
  link does not claim that a particular tag exists.
- Recursive Git tree truncation never becomes false `missing`; affected
  path-based rules return `unavailable`.
- Evidence paths are removed from private-repository reports in every format.
