# Development contract

Preserve fail-closed semantics. Work spec first, tests second, code third.

- Missing, blocked, invalid, or failed evidence must never become `CONTINUE`.
- Do not weaken or skip a failing test to obtain green CI.
- Reject duplicate JSON keys and unknown core fields.
- Keep v0.1 dependency-free, offline, deterministic, and free of telemetry.
- Do not claim that a stored SHA-256 fingerprint was resolved or verified.
- Record explicit coverage and collection failures; zero is not self-explanatory.
