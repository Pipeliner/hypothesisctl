# Repository-native discovery contract

The project has one static GitHub Pages landing page at
`https://pipeliner.github.io/hypothesisctl/`. Its job is to make the public
repository intelligible to search engines and first-time visitors without adding
a service, telemetry system, or separate product surface.

The page must:

- state the fail-closed job and distinguish `KILL`, `BLOCKED`, `WAIT`, and
  `CONTINUE`;
- show the dependency-free GitHub Action path and link to the exact public
  repository, release, agent example, security policy, and license;
- use a canonical URL, unique title and description, Open Graph metadata, and one
  valid `SoftwareApplication` JSON-LD object;
- be usable on narrow screens and with keyboard navigation;
- contain no JavaScript execution, analytics, cookies, forms, remote fonts,
  remote stylesheets, trackers, or third-party images; and
- avoid assurance claims: the tool validates record structure and deterministic
  policy semantics, but it does not prove that evidence bytes or user assertions
  are true.

`docs/robots.txt` permits indexing and points to a valid XML sitemap containing
only the canonical landing page. Tests parse the HTML, JSON-LD, and XML with
format-appropriate parsers and reject external executable/resource ingress.

Publishing uses GitHub Pages' repository-native branch source from `main` and
`/docs`; no deployment Action or credential is added. The repository homepage
metadata points to the Pages URL. Page availability and rendered metadata must be
verified over HTTPS after GitHub reports a successful Pages build. A configured
site is not called discoverable until that runtime check succeeds. It is not called adopted without traffic or star evidence.
