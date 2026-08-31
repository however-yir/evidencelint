# No-clone GitHub Action

EvidenceLint includes a composite Action that reads the target repository
through GitHub REST APIs. It does not use `actions/checkout`, clone the target,
or execute target code.

Use the published `v0.2.0` tag:

```yaml
name: Evidence audit

on:
  workflow_dispatch:
  schedule:
    - cron: "17 3 * * 1"

permissions:
  contents: read
  checks: read

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Audit repository evidence
        id: evidencelint
        uses: however-yir/evidencelint@v0.2.0
        with:
          format: markdown
          output: evidencelint-report.md
          strict: "false"
          token: ${{ github.token }}

      - name: Upload report
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: evidencelint-report
          path: ${{ steps.evidencelint.outputs.report }}
```

No target checkout step is needed. The Action defaults to the workflow's own
repository; set `repository: owner/name` to audit another repository that the
token can read.

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `repository` | current workflow repository | Target in `owner/name` form |
| `format` | `markdown` | `text`, `json`, or `markdown` |
| `output` | `evidencelint-report.md` | Report path in the workflow workspace |
| `strict` | `false` | Exit non-zero for `failed` or `missing` rules |
| `policy` | empty | Local `evidencelint-policy-v1` JSON file |
| `baseline` | empty | Earlier JSON report; enables offline comparison mode |
| `token` | `github.token` | Read-only API token |

The caller controls token permissions. EvidenceLint only sends REST `GET`
requests and never writes the token into reports.

## Strict-mode caution

Strict mode treats missing engineering evidence as a failing result. Enable it
after reviewing the first report; profile repositories and non-distributable
projects may intentionally lack Releases, environment templates, or tests.

When `baseline` is supplied, strict mode fails only for a newly introduced
Policy blocker. EvidenceLint itself still does not checkout a target repository;
the workflow author is responsible for making a baseline or Policy file
available in the workspace.
