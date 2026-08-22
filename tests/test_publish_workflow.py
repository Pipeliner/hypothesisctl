import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


class PublishWorkflowTest(unittest.TestCase):
    def load_workflow(self):
        return json.loads(
            (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")
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

    def test_release_contract_names_exact_pending_publisher(self):
        contract = (ROOT / "RELEASING.md").read_text(encoding="utf-8")
        for value in (
            "PyPI project: `hypothesisctl`",
            "GitHub owner: `Pipeliner`",
            "repository: `hypothesisctl`",
            "workflow: `publish.yml`",
            "environment: `pypi`",
            "require owner approval",
        ):
            self.assertIn(value, contract)


if __name__ == "__main__":
    unittest.main()
