# Changelog

All notable changes are documented here.

## Unreleased

- Add a tested AI-agent completion example that stays `BLOCKED` until an
  independent review exists, with explicit zero-result coverage.
- Put the dependency-free GitHub Action path into the first-use README flow.

## 0.2.0 — 2026-08-22

- Add a dependency-free composite GitHub Action that runs the bundled CLI.
- Pass action inputs through quoted environment variables and cover shell-injection
  behavior mechanically.
- Add a real, coverage-qualified release-gate example and action smoke test.

## 0.1.0 — 2026-08-22

- Add strict, versioned JSON hypothesis records.
- Add deterministic `validate`, `evaluate`, and CI-oriented `check` commands.
- Distinguish `CONTINUE`, `KILL`, `BLOCKED`, and `WAIT` with stable exit codes.
- Preserve coverage, unscanned areas, and collection failures in evaluation output.
- Reject duplicate keys, unknown fields, floats, invalid UTF-8, excessive nesting,
  and oversized input.
