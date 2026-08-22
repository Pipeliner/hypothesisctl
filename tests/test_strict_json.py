import json
from pathlib import Path
import tempfile
import unittest

from hypothesisctl.core import ValidationError
from hypothesisctl.strict_json import MAX_BYTES, load_file, loads_strict


class StrictJsonTest(unittest.TestCase):
    def test_rejects_duplicate_keys_at_any_depth(self):
        for text in ('{"a":1,"a":2}', '{"a":{"b":1,"b":2}}'):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                loads_strict(text.encode())

    def test_rejects_floats_and_non_finite_numbers(self):
        for value in ("1.0", "1e3", "NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                loads_strict(("{\"value\":" + value + "}").encode())

    def test_rejects_invalid_utf8_and_oversize_input(self):
        with self.assertRaises(ValidationError):
            loads_strict(b"\xff")
        with self.assertRaises(ValidationError):
            loads_strict(b" " * (MAX_BYTES + 1))

    def test_accepts_exact_size_limit_then_reports_json_error(self):
        with self.assertRaisesRegex(ValidationError, "JSON"):
            loads_strict(b" " * MAX_BYTES)

    def test_rejects_nesting_beyond_limit(self):
        with self.assertRaises(ValidationError):
            loads_strict(("[" * 65 + "0" + "]" * 65).encode())

    def test_load_file_reports_missing_and_non_regular_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValidationError):
                load_file(root / "missing.json")
            with self.assertRaises(ValidationError):
                load_file(root)


if __name__ == "__main__":
    unittest.main()
