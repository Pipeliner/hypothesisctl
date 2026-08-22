import json
import unittest

from hypothesisctl.core import ValidationError, evaluate, validate_record

from tests.helpers import DIGEST, cloned, gate, record


class CoreTest(unittest.TestCase):
    def test_rejects_identifiers_that_can_spoof_text_output(self):
        for identifier in ("bad\nCONTINUE", "\x1b[31mfail", "two words", "x" * 129):
            candidate = record()
            candidate["policies"][0]["id"] = identifier
            with self.subTest(identifier=repr(identifier)):
                with self.assertRaisesRegex(ValidationError, "ASCII slug"):
                    validate_record(candidate)

    def test_all_four_decisions(self):
        expected = {
            ("pass",): "CONTINUE",
            ("unknown",): "WAIT",
            ("blocked",): "BLOCKED",
            ("fail",): "KILL",
        }
        for statuses, decision in expected.items():
            with self.subTest(statuses=statuses):
                result = evaluate(validate_record(record(statuses)))
                self.assertEqual(result["decisions"]["launch"]["decision"], decision)

    def test_precedence_is_fail_blocked_unknown_pass(self):
        result = evaluate(validate_record(record(("pass", "unknown", "blocked", "fail"))))
        decision = result["decisions"]["launch"]
        self.assertEqual(decision["decision"], "KILL")
        self.assertEqual(decision["controlling_status"], "fail")
        self.assertEqual(decision["contributing_gates"], ["g4"])

    def test_rejects_duplicate_gate_and_policy_ids(self):
        duplicate_gate = record()
        duplicate_gate["gates"].append(cloned(duplicate_gate["gates"][0]))
        duplicate_policy = record()
        duplicate_policy["policies"].append(cloned(duplicate_policy["policies"][0]))
        for candidate in (duplicate_gate, duplicate_policy):
            with self.assertRaises(ValidationError):
                validate_record(candidate)

    def test_rejects_duplicate_or_unknown_policy_references(self):
        duplicate = record()
        duplicate["policies"][0]["requires"] = ["g1", "g1"]
        unknown = record()
        unknown["policies"][0]["requires"] = ["missing"]
        for candidate in (duplicate, unknown):
            with self.assertRaises(ValidationError):
                validate_record(candidate)

    def test_rejects_unknown_fields_recursively(self):
        candidates = []
        for path in ("root", "hypothesis", "gate", "evidence", "coverage", "policy"):
            candidate = record()
            target = {
                "root": candidate,
                "hypothesis": candidate["hypothesis"],
                "gate": candidate["gates"][0],
                "evidence": candidate["gates"][0]["evidence"][0],
                "coverage": candidate["gates"][0]["coverage"],
                "policy": candidate["policies"][0],
            }[path]
            target["unexpected"] = True
            candidates.append(candidate)
        for candidate in candidates:
            with self.assertRaises(ValidationError):
                validate_record(candidate)

    def test_pass_and_fail_require_evidence(self):
        for status in ("pass", "fail"):
            candidate = record((status,))
            candidate["gates"][0]["evidence"] = []
            with self.subTest(status=status), self.assertRaises(ValidationError):
                validate_record(candidate)

    def test_pass_requires_positive_clean_coverage(self):
        zero = record()
        zero["gates"][0]["coverage"]["observed"] = 0
        failed_collection = record()
        failed_collection["gates"][0]["coverage"]["collection_failures"] = ["timeout"]
        for candidate in (zero, failed_collection):
            with self.assertRaises(ValidationError):
                validate_record(candidate)

    def test_rejects_boolean_observed_and_bad_digest(self):
        boolean = record()
        boolean["gates"][0]["coverage"]["observed"] = True
        digest = record()
        digest["gates"][0]["evidence"][0]["sha256"] = "A" * 64
        for candidate in (boolean, digest):
            with self.assertRaises(ValidationError):
                validate_record(candidate)

    def test_reordering_does_not_change_semantic_results(self):
        original = record(("unknown", "fail", "blocked"))
        reordered = cloned(original)
        reordered["gates"].reverse()
        reordered["policies"].reverse()
        self.assertEqual(
            json.dumps(evaluate(validate_record(original)), sort_keys=True),
            json.dumps(evaluate(validate_record(reordered)), sort_keys=True),
        )

    def test_zero_result_coverage_remains_in_evaluation(self):
        result = evaluate(validate_record(record(("unknown",))))
        coverage = result["coverage"]["g1"]
        self.assertEqual(coverage["observed"], 0)
        self.assertEqual(coverage["unscanned"], ["remaining population"])

    def test_policy_selection_is_exact(self):
        candidate = record()
        candidate["policies"].append({"id": "second", "requires": ["g1"]})
        result = evaluate(validate_record(candidate), "second")
        self.assertEqual(list(result["decisions"]), ["second"])
        with self.assertRaises(ValidationError):
            evaluate(validate_record(candidate), "missing")


if __name__ == "__main__":
    unittest.main()
