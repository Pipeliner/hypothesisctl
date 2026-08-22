# Contributing

Issues and pull requests are welcome.

## Development

Python 3.10 or newer is required. The project has no runtime dependencies.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Please preserve the implementation order for behavior changes:

1. update `SPEC.md` and the JSON Schema;
2. add or change a failing test;
3. implement the smallest change that makes the suite pass.

Fail-closed behavior is the core invariant: missing, blocked, invalid, or failed
evidence must never become `CONTINUE`. Do not weaken or skip tests to obtain a
green build.
