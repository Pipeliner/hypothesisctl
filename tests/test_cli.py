import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import record


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run_cli(*args, cwd=ROOT):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    return subprocess.run(
        [sys.executable, "-m", "hypothesisctl", *map(str, args)],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class CliTest(unittest.TestCase):
    def write_record(self, directory, statuses=("pass",)):
        path = Path(directory) / "hypothesis.json"
        path.write_text(json.dumps(record(statuses)), encoding="utf-8")
        return path

    def test_init_creates_valid_wait_record_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.json"
            created = run_cli("init", path)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(created.stderr, "")
            validated = run_cli("validate", path, "--format", "json")
            self.assertEqual(validated.returncode, 0, validated.stderr)
            evaluated = run_cli("evaluate", path, "--format", "json")
            self.assertEqual(
                json.loads(evaluated.stdout)["decisions"]["ship"]["decision"],
                "WAIT",
            )
            before = path.read_bytes()
            collision = run_cli("init", path)
            self.assertEqual(collision.returncode, 2)
            self.assertEqual(path.read_bytes(), before)

    def test_validate_text_and_json_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_record(directory)
            text = run_cli("validate", path)
            machine = run_cli("validate", path, "--format", "json")
            self.assertEqual(text.returncode, 0, text.stderr)
            self.assertEqual(text.stdout, "valid\n")
            self.assertEqual(json.loads(machine.stdout), {"schema_version": "1", "valid": True})

    def test_evaluate_text_and_json_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_record(directory, ("unknown",))
            first = run_cli("evaluate", path, "--format", "json")
            second = run_cli("evaluate", path, "--format", "json")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            text = run_cli("evaluate", path)
            self.assertEqual(text.stdout, "launch: WAIT (unknown: g1)\n")

    def test_check_maps_each_decision_to_exit_code(self):
        expected = {"pass": 0, "fail": 4, "unknown": 5, "blocked": 6}
        with tempfile.TemporaryDirectory() as directory:
            for status, exit_code in expected.items():
                path = self.write_record(directory, (status,))
                result = run_cli("check", path, "--policy", "launch", "--format", "json")
                with self.subTest(status=status):
                    self.assertEqual(result.returncode, exit_code, result.stderr)
                    self.assertEqual(
                        json.loads(result.stdout)["decision"],
                        {"pass": "CONTINUE", "fail": "KILL", "unknown": "WAIT", "blocked": "BLOCKED"}[status],
                    )

    def test_invalid_input_uses_stderr_and_exit_three(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            result = run_cli("validate", path, "--format", "json")
            self.assertEqual(result.returncode, 3)
            self.assertEqual(result.stdout, "")
            self.assertIn("duplicate", result.stderr.lower())

    def test_non_init_commands_do_not_mutate_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_record(directory)
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            for command in (
                ("validate", path),
                ("evaluate", path),
                ("check", path, "--policy", "launch"),
            ):
                result = run_cli(*command)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_example_commands_are_executable(self):
        example = ROOT / "examples" / "product-hypothesis.json"
        validated = run_cli("validate", example)
        evaluated = run_cli("evaluate", example, "--format", "json")
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(evaluated.returncode, 0, evaluated.stderr)
        self.assertEqual(json.loads(evaluated.stdout)["decisions"]["ship"]["decision"], "WAIT")

        release_example = ROOT / "examples" / "release-gate.json"
        release = run_cli("check", release_example, "--policy", "publish", "--format", "json")
        self.assertEqual(release.returncode, 0, release.stderr)
        self.assertEqual(json.loads(release.stdout)["decision"], "CONTINUE")


if __name__ == "__main__":
    unittest.main()
