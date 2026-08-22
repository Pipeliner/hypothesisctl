# Security policy

## Supported versions

Security fixes are applied to the latest released version.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not
include credentials, personal data, or exploit data from systems you do not own.

You should receive an acknowledgement within seven days. Public disclosure can
be coordinated after a fix or mitigation is available.

## Security boundaries

`hypothesisctl` parses local JSON and prints a decision. It does not access the
network, execute evidence, resolve evidence references, or verify referenced
bytes. Treat records and referenced evidence as untrusted data.
