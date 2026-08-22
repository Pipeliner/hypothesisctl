# Changelog

All notable changes are documented here.

## 0.1.0 — 2026-08-22

- Add strict, versioned JSON hypothesis records.
- Add deterministic `validate`, `evaluate`, and CI-oriented `check` commands.
- Distinguish `CONTINUE`, `KILL`, `BLOCKED`, and `WAIT` with stable exit codes.
- Preserve coverage, unscanned areas, and collection failures in evaluation output.
- Reject duplicate keys, unknown fields, floats, invalid UTF-8, excessive nesting,
  and oversized input.
