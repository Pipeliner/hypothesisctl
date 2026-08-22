# hypothesisctl v0.1 contract

`hypothesisctl` is an experimental, dependency-free Python CLI that makes a
falsification policy executable in CI.

It evaluates required gate statuses with fixed precedence:

1. any `fail` → `KILL`;
2. otherwise any `blocked` → `BLOCKED`;
3. otherwise any `unknown` → `WAIT`;
4. every required gate `pass` → `CONTINUE`.

The versioned JSON contract is defined by `schema/hypothesis-v1.schema.json` and
the stricter semantic checks in this document. Unknown fields, duplicate keys,
floats, non-finite numbers, booleans where integers are required, files above
1 MiB, and nesting beyond 64 levels are invalid.

A gate records `criterion`, `status`, `rationale`, immutable evidence references,
and coverage. Each evidence reference contains a `ref` plus a lowercase SHA-256
fingerprint. Version 0.1 validates the fingerprint's shape but does not resolve or
verify evidence bytes. A `pass` or `fail` requires evidence. A `pass` additionally
requires positive observed coverage and zero collection failures.

Hypothesis, gate, and policy identifiers are 1–128 character ASCII slugs. They
start with an alphanumeric character and otherwise contain only alphanumerics,
periods, underscores, or hyphens. This keeps text-mode CI output single-line.

Commands are `init`, `validate`, `evaluate`, and `check`. `check` exits 0 for
`CONTINUE`, 4 for `KILL`, 5 for `WAIT`, and 6 for `BLOCKED`. Usage/init collision
is 2, invalid input is 3, and unexpected internal error is 10. Only `init` writes,
and it never overwrites an existing file.

There is no server, network access, telemetry, YAML parser, plugin system,
attestation layer, evidence downloader, universal score, or stable Python API.

## Composite GitHub Action

The repository root may be used as a composite GitHub Action. Its stable inputs
are `record`, `policy`, and optional `format` (`text` by default). The action
invokes the bundled Python source directly and preserves the `check` command's
stdout, stderr, and exit code. Inputs cross the shell boundary through quoted
environment variables, not interpolated command text. The action performs no
install, dependency resolution, network request, evidence resolution, or write.
