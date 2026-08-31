# v0.1.0 release verification

The GitHub release is published from `however-yir/evidencelint`. PyPI
publication is intentionally outside the v0.1.0 scope.

## Completed locally

- Package and CLI versions are `0.1.0`.
- Python 3.9 and 3.13 CI jobs are defined.
- Offline tests and bytecode compilation are required by CI.
- Wheel construction and clean-wheel installation are required by CI.
- The composite Action audits through GitHub APIs without checking out the
  target repository.
- Live no-clone reports and portfolio examples are included.
- Rule, privacy, security, contribution, and known-limit documentation exists.
- Account-wide local reports are ignored from version control and excluded from
  source distributions because aggregate metadata can reveal private
  repository names.

## GitHub publication

1. Public repository created with reviewed description and topics.
2. Initial commit pushed after confirming ignored local reports were not staged.
3. Python, package, and Action smoke jobs passed on GitHub-hosted CI.
4. Exact `v0.1.0` tag pushed from the verified default-branch commit.
5. GitHub Release created with wheel and source-distribution assets.
6. Repository, tag, Release assets, and default-branch checks read back through
   the GitHub API.

## Not published

PyPI publication was not requested. If added later, verify name ownership and
use trusted publishing rather than a long-lived API token.
