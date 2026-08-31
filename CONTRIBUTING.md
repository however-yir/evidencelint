# Contributing

Keep changes narrow and evidence-first.

## Local checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall -q src tests scripts
python3 -m pip wheel --no-deps --wheel-dir dist .
```

Every rule change needs at least one positive and one negative or unavailable
case. A missing API response must never silently become missing repository
evidence.

Release-facing changes must also keep the version in `pyproject.toml` and
`src/evidencelint/__init__.py` synchronized, preserve Python 3.9 compatibility,
and pass the no-clone Action boundary tests.

Run the `Future release` workflow manually before publishing a new version.
Manual runs build and verify the candidate on Python 3.9 and 3.13 without
publishing. A later `vX.Y.Z` tag must exactly match the package version before
the workflow receives permission to create the GitHub Release. PyPI remains a
separate, intentionally unsupported publication path.
Candidate installation is preceded by verification of the generated
`SHA256SUMS`; the same checksum file is included in tag-created Releases.
GitHub-authored Actions are pinned to full commit identifiers. Update a pin
only after reviewing the corresponding upstream release, and keep its version
comment synchronized for auditability.

## Rule design

A rule should:

1. name the exact evidence it consumes;
2. explain what it cannot prove;
3. preserve `unavailable` when collection coverage is incomplete;
4. return stable evidence locators instead of raw source content;
5. avoid a subjective composite score.
