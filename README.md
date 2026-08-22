# hypothesisctl

[![test](https://github.com/Pipeliner/hypothesisctl/actions/workflows/test.yml/badge.svg)](https://github.com/Pipeliner/hypothesisctl/actions/workflows/test.yml)

**Stop CI—and AI agents—from declaring victory before the evidence exists.**

`hypothesisctl` turns a falsifiable hypothesis and its evidence gates into a
deterministic CI decision. It refuses to call an experiment validated when
evidence is missing, collection failed, or a required gate is blocked.

```text
$ hypothesisctl check examples/product-hypothesis.json --policy ship
ship: WAIT (unknown: conversion-lift)
$ echo $?
5
```

## Why

Experiment documents tend to blur four materially different states:

| Evidence state | Decision | Exit code |
|---|---:|---:|
| Every required gate passed | `CONTINUE` | 0 |
| Any required gate failed | `KILL` | 4 |
| No failure, but a gate is blocked | `BLOCKED` | 6 |
| No failure or block, but evidence is unknown | `WAIT` | 5 |

The fixed precedence is `KILL > BLOCKED > WAIT > CONTINUE`. Missing or invalid
input never produces `CONTINUE`.

## Install

Python 3.10 or newer is required. The CLI has no runtime dependencies and does
not use the network or telemetry. Install the tagged source from GitHub:

```bash
python -m pip install "git+https://github.com/Pipeliner/hypothesisctl.git@v0.2.0"
```

For a source checkout:

```bash
python -m pip install .
```

## Quick start

Create a record:

```bash
hypothesisctl init hypothesis.json
```

Edit its hypothesis, gates, evidence fingerprints, coverage, and policies. Then:

```bash
hypothesisctl validate hypothesis.json
hypothesisctl evaluate hypothesis.json
hypothesisctl check hypothesis.json --policy ship
```

Use `--format json` for machine-readable output:

```bash
hypothesisctl evaluate hypothesis.json --format json
```

## Record format

Each gate has a preregistered criterion, one of four statuses, a rationale,
immutable evidence references, and coverage:

```json
{
  "id": "conversion-lift",
  "criterion": "Qualified trial starts improve by at least 15%.",
  "status": "unknown",
  "rationale": "The analysis has not completed.",
  "evidence": [],
  "coverage": {
    "population": "Qualified visitors in both variants",
    "observed": 0,
    "unscanned": ["All outcome rows pending analysis"],
    "collection_failures": []
  }
}
```

See the complete [example](examples/product-hypothesis.json), the
[v0.1 contract](SPEC.md), and the machine-readable
[JSON Schema](schema/hypothesis-v1.schema.json).

Important semantics:

- A `pass` or `fail` gate requires at least one evidence reference.
- A `pass` requires positive observed coverage and no collection failures.
- Evidence references contain a lowercase SHA-256 fingerprint. Version 0.1
  validates its shape but does **not** fetch evidence or verify its bytes.
- Duplicate keys, unknown fields, floats, invalid UTF-8, excessive nesting, and
  inputs above 1 MiB are rejected.
- Hypothesis, gate, and policy identifiers are bounded ASCII slugs, preventing
  multiline or terminal-control injection in text-mode CI output.
- Only `init` writes a file, and it refuses to overwrite an existing path.

## GitHub Action

The repository is a dependency-free composite Action. Pin the immutable commit
when the workflow is part of a supply-chain boundary:

```yaml
permissions:
  contents: read

steps:
  - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
  - name: Enforce experiment gate
    uses: Pipeliner/hypothesisctl@1722321620d8c297562bcf20ec1bd63057407df1 # v0.2.0 action
    with:
      record: hypothesis.json
      policy: ship
      format: json
```

The Action runs the bundled source directly. It does not install dependencies,
resolve evidence, use the network, or interpolate inputs into shell code.

## Installed CLI in CI

```yaml
- name: Enforce experiment gate
  run: hypothesisctl check hypothesis.json --policy ship
```

Only `CONTINUE` exits zero. A failed, blocked, unknown, or invalid decision
therefore stops the job without special shell logic.

## Scope

Version 0.2 is intentionally small: one local JSON record, one CLI, one composite
Action, and deterministic evaluation. It has no server, YAML parser, plugin
system, evidence downloader, attestation layer, universal score, network access,
or stable Python API.

Please report vulnerabilities according to [SECURITY.md](SECURITY.md). Contributions
are welcome under [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
