"""JSON export: the ResearchOutcome, verbatim, as one JSON document."""

import json


def export_json(outcome, path) -> None:
    payload = {
        "request": outcome.request,
        "plan": outcome.plan,
        "sources": outcome.sources,
        "records": outcome.records,
        "validation_problems": outcome.validation_problems,
        "duplicate_groups": outcome.duplicate_groups,
        "verification_by_group": outcome.verification_by_group,
        "completeness": outcome.completeness,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
