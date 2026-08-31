# EvidenceLint - Project Plan

## Concept Lock

**One-liner:** EvidenceLint helps maintainers and reviewers verify the current
engineering evidence behind a GitHub AI project without cloning or running its
code.

**Primary users:** open-source maintainers, AI engineering candidates,
technical reviewers, and recruiters who need inspectable facts instead of
README-only claims.

**Problem:** GitHub project pages mix marketing claims, old badges, generated
documentation, and real engineering evidence. Reviewers need a safe way to
separate what is currently verified from what is missing or unavailable.

## Scope Fence

### V1 features

1. Read-only GitHub REST collection for one `owner/repo` target or every
   repository owned by the authenticated account.
2. Versioned evidence snapshot covering metadata, current CI, tree, README,
   release, and license signals.
3. Deterministic rules for quality, evaluation, security, provenance, and
   documentation evidence.
4. Text, JSON, and Markdown reports with explicit status semantics.
5. Offline regression fixtures plus public and authenticated portfolio smoke
   paths.

### Not yet

- Repository cloning, checkout, or execution of untrusted project code.
- Automated repair, README edits, issue creation, or other GitHub mutations.
- LLM-generated scoring in the trust path.
- A single composite score that hides dimension-level uncertainty.
- Hosted accounts, dashboards, scheduled monitoring, or organization billing.
- Full source-level security scanning or plagiarism/originality detection.

## Architecture

```text
CLI
 ├─ single scan ──────────────┐
 └─ owned-account batch ────────┤ (bounded workers)
                                 ↓
                            Collector
                                 └─ GitHub REST client (read-only)
                                     ├─ repository metadata
                                     ├─ default-branch commit + check runs
                                     ├─ recursive Git tree
                                     ├─ README
                                     └─ latest release
                                          ↓
                                  RepositorySnapshot
                                          ↓
                                  deterministic rules
                                          ↓
                         AuditReport / BatchReport
                                          ↓
                              text / JSON / Markdown
```

The transport and rule engine remain separate so tests can provide fixed API
responses without network access.

## Timeline and checkpoints

| Phase | Dates | Deliverable | Exit check | Dependency | Status |
|---|---|---|---|---|---|
| M0 vertical slice | Aug 31-Sep 2 | `scan -> report` CLI | Public repo produces a stable report | none | complete Aug 31 |
| M1 collector hardening | Sep 3-6 | pagination, rate-limit, permissions, batch scan | 15/15 repositories collected with isolated failures and no private evidence paths | M0 | complete Aug 31 |
| M2 rule set | Sep 7-13 | six evidence dimensions | every declared rule status has a reachability regression | M1 | complete Aug 31 |
| M3 claim links | Sep 14-20 | README path, badge and release checks | seeded broken claims fail deterministically | M2 | complete Aug 31 |
| M4 portfolio dogfood | Sep 21-27 | 15-repository matrix and action report | every owned repository has a timestamped result and classified action queue | M3 | complete Aug 31 |
| M5 public MVP | Sep 28-Oct 11 | docs, package, Action, v0.1.0 | fresh install and public example pass | M4 | complete Aug 31 |

The schedule assumes one developer at 70% capacity and includes roughly 20%
buffer for GitHub API edge cases.

The first portfolio baseline was completed early during M1. It validates the
collector but does not replace M2-M3 rule coverage or the final M4 dogfood gate.

M5 GitHub publication is complete. PyPI was deliberately excluded from the
release scope.

## Work breakdown and critical path

1. Stabilize the snapshot schema.
2. Harden GitHub collection and error classification.
3. Freeze rule identifiers and status semantics.
4. Add report formats and deterministic fixtures.
5. Dogfood against the 15-repository portfolio.
6. Publish installation and release evidence.

Items 1-3 are the critical path. Documentation examples and report styling can
run alongside fixture expansion after the schema is stable.

## Quality gates

- Runtime dependency count remains zero until a dependency has measured value.
- Unit tests never require network access.
- Live smoke tests are explicit and non-blocking for normal unit tests.
- Tokens, credentials, README contents, and private repository paths are never
  copied into reports by default.
- Tree truncation, permission denial, and API failure produce `unavailable`.
- Every report records target, capture time, default-branch SHA, and schema
  version.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| GitHub rate limits | incomplete scans | token discovery, bounded calls, explicit unavailable status |
| Recursive tree truncation | false missing evidence | detect `truncated`, suppress path-based absence claims |
| README wording ambiguity | false claim verification | V1 verifies resolvable artifacts, not semantic truth |
| Private repository leakage | sensitive report contents | store counts and evidence locators, not raw README or source |
| Rule gaming | misleading green result | publish rule limits and keep dimensions separate |
| Scope growth into a platform | delayed release | enforce the V1 not-yet list and vertical checkpoints |

## Success criteria

- One command audits a public repository without cloning or mutation.
- The same fixture always yields byte-stable structured findings apart from the
  capture timestamp.
- A broken README path, red current check run, absent security policy, and
  truncated tree are classified correctly.
- The tool can audit all 15 owned repositories, including private ones when an
  authorized token is available, without exposing credentials.
- v0.1.0 includes a reproducible sample report and a documented limitations
  section.
