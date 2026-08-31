# EvidenceLint report comparison

`compare` is an offline operation. It never contacts GitHub and never executes
repository code.

```bash
evidencelint compare baseline.json current.json --format markdown --strict
```

The reports must describe the same repository, contain the same rule IDs, and
use the same rule-set version. Changes are classified as `new_blocker`,
`resolved_blocker`, `changed`, or `unchanged`. Strict comparison fails only for
`new_blocker`; an existing unresolved gap does not repeatedly block the same
baseline comparison.

Comparison reports contain status transitions, not source diffs or a composite
quality score. Treat baseline reports for private repositories as sensitive.
