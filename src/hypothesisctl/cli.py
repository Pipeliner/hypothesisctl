import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .core import ValidationError, evaluate, validate_record
from .strict_json import load_file


CHECK_EXITS = {"CONTINUE": 0, "KILL": 4, "WAIT": 5, "BLOCKED": 6}

STARTER = {
    "schema_version": "1",
    "hypothesis": {
        "id": "my-experiment",
        "statement": "State the falsifiable hypothesis.",
        "owner": "team-or-person",
    },
    "gates": [
        {
            "id": "evidence-gate",
            "criterion": "State the evidence threshold that must pass.",
            "status": "unknown",
            "rationale": "Evidence has not been collected yet.",
            "evidence": [],
            "coverage": {
                "population": "State the target population.",
                "observed": 0,
                "unscanned": ["The target population has not been scanned."],
                "collection_failures": [],
            },
        }
    ],
    "policies": [{"id": "ship", "requires": ["evidence-gate"]}],
}


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def _format_decisions(result: dict[str, Any]) -> str:
    lines = []
    for policy_id, decision in result["decisions"].items():
        gates = ", ".join(decision["contributing_gates"])
        lines.append(
            f"{policy_id}: {decision['decision']} "
            f"({decision['controlling_status']}: {gates})"
        )
    return "\n".join(lines) + "\n"


def _record(path: str) -> dict[str, Any]:
    return validate_record(load_file(path))


def _add_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hypothesisctl",
        description="Fail-closed decision gates for experiments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create a starter record")
    init.add_argument("path", nargs="?", default="hypothesis.json")

    validate = subparsers.add_parser("validate", help="validate a record")
    validate.add_argument("record")
    _add_format(validate)

    evaluate_parser = subparsers.add_parser("evaluate", help="evaluate policies")
    evaluate_parser.add_argument("record")
    evaluate_parser.add_argument("--policy")
    _add_format(evaluate_parser)

    check = subparsers.add_parser("check", help="evaluate one policy for CI")
    check.add_argument("record")
    check.add_argument("--policy", required=True)
    _add_format(check)
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "init":
        path = Path(args.path)
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(STARTER, indent=2, sort_keys=True) + "\n")
        except FileExistsError as error:
            raise FileExistsError(f"refusing to overwrite existing file: {path}") from error
        print(f"created {path}")
        return 0

    record = _record(args.record)
    if args.command == "validate":
        if args.format == "json":
            sys.stdout.write(_json({"schema_version": record["schema_version"], "valid": True}))
        else:
            print("valid")
        return 0

    result = evaluate(record, args.policy)
    if args.command == "evaluate":
        sys.stdout.write(_json(result) if args.format == "json" else _format_decisions(result))
        return 0

    decision = result["decisions"][args.policy]
    output = {"policy": args.policy, **decision}
    if args.format == "json":
        sys.stdout.write(_json(output))
    else:
        sys.stdout.write(_format_decisions({"decisions": {args.policy: decision}}))
    return CHECK_EXITS[decision["decision"]]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except FileExistsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except ValidationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 3
    except Exception as error:
        print(f"internal error: {error}", file=sys.stderr)
        return 10
