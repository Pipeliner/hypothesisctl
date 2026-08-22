import copy


DIGEST = "a" * 64


def gate(gate_id="problem", status="pass"):
    evidence = [] if status in {"unknown", "blocked"} else [
        {"ref": f"evidence/{gate_id}.md", "sha256": DIGEST}
    ]
    observed = 0 if status in {"unknown", "blocked"} else 1
    return {
        "id": gate_id,
        "criterion": f"Criterion for {gate_id}",
        "status": status,
        "rationale": f"Rationale for {gate_id}",
        "evidence": evidence,
        "coverage": {
            "population": f"Population for {gate_id}",
            "observed": observed,
            "unscanned": ["remaining population"] if observed == 0 else [],
            "collection_failures": [],
        },
    }


def record(statuses=("pass",)):
    gates = [gate(f"g{index + 1}", status) for index, status in enumerate(statuses)]
    return {
        "schema_version": "1",
        "hypothesis": {
            "id": "example",
            "statement": "A falsifiable statement",
            "owner": "team",
        },
        "gates": gates,
        "policies": [{"id": "launch", "requires": [item["id"] for item in gates]}],
    }


def cloned(value):
    return copy.deepcopy(value)
