import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.helpers import record


ROOT = Path(__file__).resolve().parents[1]


class CompositeActionTest(unittest.TestCase):
    def run_action(self, record_path, policy):
        metadata = json.loads((ROOT / "action.yml").read_text(encoding="utf-8"))
        env = os.environ.copy()
        env.update(
            {
                "GITHUB_ACTION_PATH": str(ROOT),
                "HYPOTHESISCTL_RECORD": str(record_path),
                "HYPOTHESISCTL_POLICY": policy,
                "HYPOTHESISCTL_FORMAT": "json",
            }
        )
        return subprocess.run(
            metadata["runs"]["steps"][0]["run"],
            shell=True,
            executable="/bin/bash",
            cwd=record_path.parent,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_metadata_is_strict_json_with_the_frozen_inputs(self):
        metadata = json.loads((ROOT / "action.yml").read_text(encoding="utf-8"))
        self.assertEqual(
            set(metadata),
            {"name", "description", "author", "inputs", "runs", "branding"},
        )
        self.assertEqual(set(metadata["inputs"]), {"record", "policy", "format"})
        self.assertTrue(metadata["inputs"]["record"]["required"])
        self.assertTrue(metadata["inputs"]["policy"]["required"])
        self.assertEqual(metadata["inputs"]["format"]["default"], "text")
        self.assertEqual(metadata["runs"]["using"], "composite")

    def test_action_uses_bundled_source_and_quoted_environment_inputs(self):
        metadata = json.loads((ROOT / "action.yml").read_text(encoding="utf-8"))
        self.assertEqual(len(metadata["runs"]["steps"]), 1)
        step = metadata["runs"]["steps"][0]
        self.assertEqual(
            set(step["env"]),
            {"HYPOTHESISCTL_RECORD", "HYPOTHESISCTL_POLICY", "HYPOTHESISCTL_FORMAT"},
        )
        command = step["run"]
        self.assertIn('PYTHONPATH="$GITHUB_ACTION_PATH/src"', command)
        self.assertIn('"$HYPOTHESISCTL_RECORD"', command)
        self.assertIn('"$HYPOTHESISCTL_POLICY"', command)
        self.assertIn('"$HYPOTHESISCTL_FORMAT"', command)
        self.assertNotIn("${{ inputs.", command)
        self.assertNotIn("pip install", command)
        self.assertNotIn("curl", command)

    def test_action_runs_from_a_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="hypothesisctl action ") as directory:
            path = Path(directory) / "experiment record.json"
            path.write_text(json.dumps(record()), encoding="utf-8")
            result = self.run_action(path, "launch")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["decision"], "CONTINUE")

    def test_action_does_not_execute_policy_text_as_shell(self):
        with tempfile.TemporaryDirectory(prefix="hypothesisctl action ") as directory:
            path = Path(directory) / "experiment.json"
            sentinel = Path(directory) / "shell-injection"
            path.write_text(json.dumps(record()), encoding="utf-8")
            result = self.run_action(path, f"launch; touch {sentinel}")
            self.assertEqual(result.returncode, 3)
            self.assertFalse(sentinel.exists())


if __name__ == "__main__":
    unittest.main()
