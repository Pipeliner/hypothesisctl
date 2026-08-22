import copy
import re
from typing import Any

from .errors import ValidationError


__all__ = ["ValidationError", "evaluate", "validate_record"]

STATUSES = {"pass", "fail", "blocked", "unknown"}
DECISIONS = {
    "pass": "CONTINUE",
    "fail": "KILL",
    "blocked": "BLOCKED",
    "unknown": "WAIT",
}
PRECEDENCE = ("fail", "blocked", "unknown", "pass")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _object(
    value: Any,
    path: str,
    required: set[str],
    allowed: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    allowed = required if allowed is None else allowed
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - allowed)
    if missing:
        raise ValidationError(f"{path} missing required fields: {', '.join(missing)}")
    if unknown:
        raise ValidationError(f"{path} has unknown fields: {', '.join(unknown)}")
    return value


def _array(value: Any, path: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be an array")
    if nonempty and not value:
        raise ValidationError(f"{path} must not be empty")
    return value


def _string(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{path} must be a string")
    if nonempty and not value.strip():
        raise ValidationError(f"{path} must not be empty")
    return value


def _string_array(value: Any, path: str) -> list[str]:
    values = _array(value, path)
    for index, item in enumerate(values):
        _string(item, f"{path}[{index}]", nonempty=False)
    return values


def _identifier(value: Any, path: str) -> str:
    identifier = _string(value, path)
    if not IDENTIFIER.fullmatch(identifier):
        raise ValidationError(
            f"{path} must be a 1-128 character ASCII slug starting with an alphanumeric"
        )
    return identifier


def _unique_id(value: Any, path: str, seen: set[str]) -> str:
    identifier = _identifier(value, path)
    if identifier in seen:
        raise ValidationError(f"duplicate identifier at {path}: {identifier}")
    seen.add(identifier)
    return identifier


def _validate_evidence(value: Any, path: str) -> list[dict[str, Any]]:
    evidence = _array(value, path)
    for index, item in enumerate(evidence):
        item_path = f"{path}[{index}]"
        entry = _object(item, item_path, {"ref", "sha256"})
        _string(entry["ref"], f"{item_path}.ref")
        digest = _string(entry["sha256"], f"{item_path}.sha256")
        if not SHA256.fullmatch(digest):
            raise ValidationError(f"{item_path}.sha256 must be 64 lowercase hex characters")
    return evidence


def _validate_coverage(value: Any, path: str) -> dict[str, Any]:
    coverage = _object(
        value,
        path,
        {"population", "observed", "unscanned", "collection_failures"},
    )
    _string(coverage["population"], f"{path}.population")
    observed = coverage["observed"]
    if isinstance(observed, bool) or not isinstance(observed, int) or observed < 0:
        raise ValidationError(f"{path}.observed must be a non-negative integer")
    _string_array(coverage["unscanned"], f"{path}.unscanned")
    _string_array(coverage["collection_failures"], f"{path}.collection_failures")
    return coverage


def validate_record(value: Any) -> dict[str, Any]:
    record = _object(
        value,
        "record",
        {"schema_version", "hypothesis", "gates", "policies"},
    )
    if record["schema_version"] != "1":
        raise ValidationError("record.schema_version must be exactly '1'")

    hypothesis = _object(
        record["hypothesis"],
        "record.hypothesis",
        {"id", "statement", "owner"},
    )
    _identifier(hypothesis["id"], "record.hypothesis.id")
    for field in ("statement", "owner"):
        _string(hypothesis[field], f"record.hypothesis.{field}")

    gates = _array(record["gates"], "record.gates", nonempty=True)
    gate_ids: set[str] = set()
    for index, item in enumerate(gates):
        path = f"record.gates[{index}]"
        gate = _object(
            item,
            path,
            {"id", "criterion", "status", "rationale", "evidence", "coverage"},
        )
        _unique_id(gate["id"], f"{path}.id", gate_ids)
        _string(gate["criterion"], f"{path}.criterion")
        status = gate["status"]
        if status not in STATUSES:
            raise ValidationError(f"{path}.status must be pass, fail, blocked, or unknown")
        _string(gate["rationale"], f"{path}.rationale")
        evidence = _validate_evidence(gate["evidence"], f"{path}.evidence")
        coverage = _validate_coverage(gate["coverage"], f"{path}.coverage")
        if status in {"pass", "fail"} and not evidence:
            raise ValidationError(f"{path} with status {status} requires evidence")
        if status == "pass" and coverage["observed"] == 0:
            raise ValidationError(f"{path} cannot pass with zero observed coverage")
        if status == "pass" and coverage["collection_failures"]:
            raise ValidationError(f"{path} cannot pass with collection failures")

    policies = _array(record["policies"], "record.policies", nonempty=True)
    policy_ids: set[str] = set()
    for index, item in enumerate(policies):
        path = f"record.policies[{index}]"
        policy = _object(item, path, {"id", "requires"})
        _unique_id(policy["id"], f"{path}.id", policy_ids)
        requires = _array(policy["requires"], f"{path}.requires", nonempty=True)
        seen_requires: set[str] = set()
        for requirement_index, gate_id in enumerate(requires):
            requirement_path = f"{path}.requires[{requirement_index}]"
            _string(gate_id, requirement_path)
            if gate_id in seen_requires:
                raise ValidationError(f"duplicate gate reference at {requirement_path}: {gate_id}")
            seen_requires.add(gate_id)
            if gate_id not in gate_ids:
                raise ValidationError(f"unknown gate reference at {requirement_path}: {gate_id}")

    return copy.deepcopy(record)


def evaluate(record: dict[str, Any], policy_id: str | None = None) -> dict[str, Any]:
    gate_map = {gate["id"]: gate for gate in record["gates"]}
    policy_map = {policy["id"]: policy for policy in record["policies"]}
    if policy_id is not None:
        _identifier(policy_id, "policy")
        if policy_id not in policy_map:
            raise ValidationError(f"unknown policy: {policy_id}")
        selected = [policy_map[policy_id]]
    else:
        selected = [policy_map[key] for key in sorted(policy_map)]

    decisions: dict[str, Any] = {}
    for policy in selected:
        statuses = {gate_id: gate_map[gate_id]["status"] for gate_id in policy["requires"]}
        controlling = next(
            status for status in PRECEDENCE if status in statuses.values()
        )
        decisions[policy["id"]] = {
            "decision": DECISIONS[controlling],
            "controlling_status": controlling,
            "contributing_gates": sorted(
                gate_id for gate_id, status in statuses.items() if status == controlling
            ),
            "gate_statuses": {key: statuses[key] for key in sorted(statuses)},
        }

    return {
        "schema_version": record["schema_version"],
        "hypothesis": copy.deepcopy(record["hypothesis"]),
        "decisions": decisions,
        "coverage": {
            key: copy.deepcopy(gate_map[key]["coverage"]) for key in sorted(gate_map)
        },
    }
