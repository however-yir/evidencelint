# Security Policy

## Supported versions

Security fixes currently target the latest `0.2.x` release and the default
branch.

## Data boundary

- Collection is read-only and uses GitHub REST `GET` endpoints.
- Tokens are discovered in memory and are never included in reports.
- Reports omit raw README content, source files, API response bodies, and token
  values.
- EvidenceLint does not clone or execute the target repository.
- The composite Action validates input shape and passes values as shell-array
  arguments rather than evaluating user-controlled strings.
- Repository workflows and the composite Action pin GitHub-authored Actions to reviewed full commit
  identifiers; version comments preserve the corresponding upstream release.

Report a suspected credential leak or unsafe API behavior through GitHub's
[private vulnerability reporting](https://github.com/however-yir/evidencelint/security/advisories/new)
before opening a public issue.
