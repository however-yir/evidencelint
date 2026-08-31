# Contributing

Keep changes narrow and evidence-first.

## Local checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall -q src tests
python3 -m pip wheel --no-deps --wheel-dir dist .
```

Every rule change needs at least one positive and one negative or unavailable
case. A missing API response must never silently become missing repository
evidence.

Release-facing changes must also keep the version in `pyproject.toml` and
`src/evidencelint/__init__.py` synchronized, preserve Python 3.9 compatibility,
and pass the no-clone Action boundary tests.

## Rule design

A rule should:

1. name the exact evidence it consumes;
2. explain what it cannot prove;
3. preserve `unavailable` when collection coverage is incomplete;
4. return stable evidence locators instead of raw source content;
5. avoid a subjective composite score.
