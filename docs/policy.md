# EvidenceLint Policy

EvidenceLint reports evidence status first. A Policy only decides whether a
missing or failed rule should block a particular project; it never removes or
changes the underlying Finding.

```json
{
  "schema_version": "evidencelint-policy-v1",
  "rules": {
    "security.environment_template": {
      "level": "advisory",
      "reason": "This CLI accepts an optional token but does not load dotenv files."
    }
  }
}
```

Rules are `required` by default. An `advisory` entry requires a reason and
remains visible in every report. Unknown rule IDs, malformed JSON, duplicate
keys, and advisory entries without reasons are rejected with exit code 2.

Use a Policy with either scan mode:

```bash
evidencelint scan owner/repo --policy policy.json --strict
evidencelint batch --policy policy.json --strict
```

The repository includes a copyable
[`examples/evidencelint-policy.json`](../examples/evidencelint-policy.json)
template. Adapt its reason to the project being audited; do not use it to hide
evidence that should be required.
