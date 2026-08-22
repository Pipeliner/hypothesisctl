# Release contract

`hypothesisctl` releases are tag-bound, reproducible enough to audit from the
declared inputs, and published without a long-lived registry token.

## PyPI channel

The PyPI project name is `hypothesisctl`. A release workflow may publish only in
response to a GitHub `release.published` event. The release tag must be exactly
`v` followed by the version in `pyproject.toml`, and checkout must use that tag
rather than the mutable default branch.

The workflow has two jobs:

1. `build` receives read-only repository permission, installs the exact
   `setuptools==83.0.0` wheel through a checked SHA-256 requirement, builds both
   wheel and source distribution, installs the wheel without dependencies, runs
   the complete tests against that installed wheel, and uploads only `dist/` as
   a short-retention workflow artifact.
2. `publish` receives no repository permission and only `id-token: write`. It
   downloads the build artifact and invokes the PyPA publishing action at an
   immutable commit with metadata verification and attestations enabled. It uses
   the protected GitHub environment named `pypi`.

No password, API token, username, `workflow_dispatch`, mutable Action tag, or
skip-existing behavior belongs in this workflow. Build and publish are separate
so code from the checkout never executes in the job that can request the PyPI
OIDC credential.

## Human gate before first upload

The repository owner must register a pending PyPI Trusted Publisher with exactly:

- PyPI project: `hypothesisctl`;
- GitHub owner: `Pipeliner`;
- repository: `hypothesisctl`;
- workflow: `publish.yml`;
- environment: `pypi`.

The `pypi` GitHub environment must require owner approval before deployment.
Publishing a release before both controls exist is prohibited. A pending
publisher does not reserve the package name, so name availability must be
rechecked immediately before the first release.

The `publish` job is additionally fail-closed behind the repository variable
`PYPI_PUBLISH_RELEASE`, which must exactly equal the release tag (for example,
`v0.2.1`). Absence, deletion, or any other value skips the publisher even when a
GitHub release is published. Setting that exact-tag variable is a separate
PyPI-distribution action and requires its own explicit gate; it never authorizes
a later version.

After publication, verify the PyPI project metadata, exact file hashes,
attestation presence, clean installation from PyPI without dependency
resolution, installed CLI behavior, and the GitHub Actions run. A release is not
complete merely because the workflow is green.
