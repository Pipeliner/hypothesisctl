import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")
UPLOAD_ARTIFACT = (
    "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
)
DOWNLOAD_ARTIFACT = (
    "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"
)


class PublishWorkflowTest(unittest.TestCase):
    def load_workflow(self):
        return json.loads(
            (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")
        )

    def load_artifact_qualification(self):
        return json.loads(
            (
                ROOT
                / ".github/workflows/artifact-transfer-qualification.yml"
            ).read_text(encoding="utf-8")
        )

    def test_trigger_is_release_only_and_tag_checkout_is_immutable(self):
        workflow = self.load_workflow()
        self.assertEqual(workflow["on"], {"release": {"types": ["published"]}})
        self.assertEqual(workflow["permissions"], {})
        build = workflow["jobs"]["build"]
        checkout = build["steps"][0]
        self.assertEqual(checkout["with"]["ref"], "${{ github.event.release.tag_name }}")
        self.assertNotIn("workflow_dispatch", json.dumps(workflow))

    def test_build_and_publish_credentials_are_separated(self):
        workflow = self.load_workflow()
        build = workflow["jobs"]["build"]
        publish = workflow["jobs"]["publish"]
        self.assertEqual(build["permissions"], {"contents": "read"})
        self.assertEqual(publish["permissions"], {"id-token": "write"})
        self.assertEqual(publish["needs"], "build")
        self.assertEqual(publish["environment"]["name"], "pypi")
        self.assertEqual(
            publish["if"],
            "${{ vars.PYPI_PUBLISH_RELEASE == github.event.release.tag_name }}",
        )
        self.assertFalse(any("checkout" in step.get("uses", "") for step in publish["steps"]))

    def test_every_action_is_immutable_and_publish_has_no_static_secret(self):
        workflow = self.load_workflow()
        steps = [
            step
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if "uses" in step
        ]
        self.assertTrue(steps)
        for step in steps:
            self.assertRegex(step["uses"], PINNED_ACTION)
        rendered = json.dumps(workflow, sort_keys=True)
        for forbidden in ("secrets.", "password", "username", "skip-existing"):
            self.assertNotIn(forbidden, rendered.lower())
        publisher = workflow["jobs"]["publish"]["steps"][-1]
        self.assertEqual(
            publisher["uses"],
            "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
        )
        self.assertTrue(publisher["with"]["attestations"])
        self.assertTrue(publisher["with"]["verify-metadata"])

    def test_build_backend_is_hash_pinned_and_artifact_is_short_lived(self):
        requirement = (ROOT / "requirements/build.txt").read_text(encoding="utf-8")
        self.assertEqual(
            requirement,
            "setuptools==83.0.0 --hash=sha256:29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3\n",
        )
        workflow = self.load_workflow()
        commands = "\n".join(
            step.get("run", "") for step in workflow["jobs"]["build"]["steps"]
        )
        self.assertIn("--require-hashes", commands)
        self.assertIn("build_sdist", commands)
        self.assertIn("build_wheel", commands)
        self.assertIn("unittest discover", commands)
        uploader = next(
            step
            for step in workflow["jobs"]["build"]["steps"]
            if step.get("uses", "").startswith("actions/upload-artifact@")
        )
        self.assertEqual(uploader["with"]["path"], "dist/")
        self.assertEqual(uploader["with"]["retention-days"], 1)

    def test_artifact_transfer_uses_exact_node24_release_commits(self):
        workflow = self.load_workflow()
        build_steps = workflow["jobs"]["build"]["steps"]
        publish_steps = workflow["jobs"]["publish"]["steps"]
        uploader = next(
            step for step in build_steps if step.get("name") == "Transfer distributions to the isolated publisher"
        )
        downloader = next(
            step for step in publish_steps if step.get("name") == "Download distributions only"
        )
        self.assertEqual(UPLOAD_ARTIFACT, uploader["uses"])
        self.assertEqual(DOWNLOAD_ARTIFACT, downloader["uses"])

        contract = (ROOT / "RELEASING.md").read_text(encoding="utf-8")
        self.assertIn(f"`{UPLOAD_ARTIFACT}`", contract)
        self.assertIn(f"`{DOWNLOAD_ARTIFACT}`", contract)
        self.assertIn("`runs.using: node24`", contract)

    def test_non_publishing_artifact_qualification_is_fail_closed(self):
        workflow = self.load_artifact_qualification()
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        rendered = json.dumps(workflow, sort_keys=True)
        self.assertNotIn("id-token", rendered)
        self.assertNotIn("pypi", rendered.lower())
        self.assertNotIn("release", json.dumps(workflow["on"]).lower())

        steps = workflow["jobs"]["artifact-transfer"]["steps"]
        absent = next(step for step in steps if step.get("id") == "absent_upload")
        self.assertEqual(UPLOAD_ARTIFACT, absent["uses"])
        self.assertTrue(absent["continue-on-error"])
        self.assertEqual("error", absent["with"]["if-no-files-found"])
        absent_assertion = next(
            step for step in steps if step.get("name") == "Require absent-path failure"
        )
        self.assertIn("steps.absent_upload.outcome", absent_assertion["run"])
        self.assertIn("failure", absent_assertion["run"])

        uploader = next(step for step in steps if step.get("id") == "upload")
        self.assertEqual(UPLOAD_ARTIFACT, uploader["uses"])
        self.assertEqual("python-package-distributions", uploader["with"]["name"])
        self.assertEqual("dist/", uploader["with"]["path"])
        self.assertEqual("error", uploader["with"]["if-no-files-found"])
        self.assertEqual(1, uploader["with"]["retention-days"])
        self.assertEqual(0, uploader["with"]["compression-level"])

        downloader = next(
            step for step in steps if step.get("name") == "Download distributions"
        )
        self.assertEqual(DOWNLOAD_ARTIFACT, downloader["uses"])
        self.assertEqual("python-package-distributions", downloader["with"]["name"])
        self.assertEqual("dist/", downloader["with"]["path"])

        commands = "\n".join(step.get("run", "") for step in steps)
        self.assertIn("sha256sum dist/*", commands)
        self.assertIn("sha256sum --check expected.sha256", commands)
        self.assertIn("cmp expected.paths actual.paths", commands)
        self.assertIn("artifact-digest", commands)
        self.assertIn("YAML.safe_load", commands)
        self.assertIn("node24", commands)

    def test_release_contract_names_exact_pending_publisher(self):
        contract = (ROOT / "RELEASING.md").read_text(encoding="utf-8")
        for value in (
            "PyPI project: `hypothesisctl`",
            "GitHub owner: `Pipeliner`",
            "repository: `hypothesisctl`",
            "workflow: `publish.yml`",
            "environment: `pypi`",
            "require owner approval",
            "PYPI_PUBLISH_RELEASE",
            "must exactly equal the release tag",
            "separate",
            "PyPI-distribution action",
        ):
            self.assertIn(value, contract)

    def test_v021_metadata_and_release_notes_are_aligned(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertRegex(pyproject, r'(?m)^version = "0\.2\.1"$')
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## 0.2.1 — 2026-08-22", changelog)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("hypothesisctl.git@v0.2.1", readme)


if __name__ == "__main__":
    unittest.main()
