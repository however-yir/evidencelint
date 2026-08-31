# EvidenceLint v0.2.0

EvidenceLint is a zero-runtime-dependency CLI and composite GitHub Action for
auditing the current engineering evidence of GitHub AI projects without
cloning or executing target code.

## Highlights

- Audits one repository or every repository owned by an authenticated account.
- Checks current default-branch CI, tests, workflows, Releases, licenses,
  evaluation assets, security guidance, provenance boundaries, README links,
  workflow badges, and explicit Release-tag links.
- Produces text, JSON, or Markdown with explicit `verified`, `partial`,
  `missing`, `failed`, `unavailable`, and `not_applicable` semantics.
- Generates a portfolio action queue that separates confirmed defects,
  collection blockers, review items, and evidence gaps without a composite
  score.
- Redacts evidence paths from private-repository reports and excludes local
  account-wide examples from public release artifacts.
- Includes a no-clone composite Action and Python 3.9/3.13 development CI.
- Adds transparent Policy evaluation: advisory findings remain visible while
  required missing or failed evidence controls strict mode.
- Adds offline comparison between compatible JSON reports, with deterministic
  new-blocker and resolved-blocker classifications.
- Adds optional Policy and baseline inputs to the composite Action.

## Verification evidence

- 56 offline tests pass on Python 3.9 and Python 3.13.
- Ruff, mypy, and 90% coverage are required in CI.
- Wheel and source distributions build without warnings.
- The wheel installs in a clean Python 3.9 environment with no runtime
  dependencies and completes a live public-repository scan.
- The Action's shell body and YAML metadata pass local validation, and an
  equivalent Action environment completed a live `ragproof` audit.

## Important limits

EvidenceLint verifies exposed GitHub artifacts, not code correctness,
originality, security, production scale, or business value. Missing evidence
does not necessarily mean software is broken. See `LIMITATIONS.md` and
`RULES.md` before enabling strict mode.
