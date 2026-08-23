"""JSON Schema validation for every model in this project, plus the one
business rule JSON Schema can't express for EventResult (score comparison
for two-participant home/away events — same limitation Step 2 documented
for result_record.schema.json).

Reuses schema/*.schema.json — no schema duplicated here.
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCHEMA_DIR = BASE_DIR / "schema"

SCHEMA_PATHS = {
    "event_result": SCHEMA_DIR / "event_result.schema.json",
    "result_record": SCHEMA_DIR / "result_record.schema.json",
    "research_request": SCHEMA_DIR / "research_request.schema.json",
    "search_plan": SCHEMA_DIR / "search_plan.schema.json",
    "search_result": SCHEMA_DIR / "search_result.schema.json",
}

_validator_cache = {}


def build_validator(schema_name: str) -> Draft202012Validator:
    if schema_name not in _validator_cache:
        schema = json.loads(SCHEMA_PATHS[schema_name].read_text())
        Draft202012Validator.check_schema(schema)
        _validator_cache[schema_name] = Draft202012Validator(schema, format_checker=FormatChecker())
    return _validator_cache[schema_name]


def _schema_errors(instance: dict, validator: Draft202012Validator) -> list:
    return [
        f"schema: {e.message} (at {'/'.join(str(p) for p in e.path) or '(root)'})"
        for e in validator.iter_errors(instance)
    ]


def event_result_matches_scores(event: dict) -> bool:
    """The one cross-field rule the schema can't express: for exactly two
    participants with roles home/away and numeric scores, `result` must
    match the score comparison. Any other participant shape (individual/
    motorsport events) has no generic arithmetic rule to check — those
    rely on `placement`, which this function doesn't second-guess."""
    status = event.get("status")
    result = event.get("result")
    participants = event.get("participants", [])

    if status in ("scheduled", "postponed", "cancelled"):
        return result is None
    if status == "abandoned":
        return result in (None, "void")

    by_role = {p.get("role"): p for p in participants if p.get("role") in ("home", "away")}
    if set(by_role) != {"home", "away"}:
        return True  # not a two-participant home/away event; nothing to check here

    home_score, away_score = by_role["home"].get("score"), by_role["away"].get("score")
    if status == "completed":
        if isinstance(home_score, (int, float)) and isinstance(away_score, (int, float)):
            if home_score > away_score:
                return result == "home_win"
            if away_score > home_score:
                return result == "away_win"
            return result == "draw"
        return result == "unknown"
    return True


def validate_event_result(event: dict) -> list:
    """Return a list of problem strings; empty list means fully valid."""
    problems = _schema_errors(event, build_validator("event_result"))
    if not event_result_matches_scores(event):
        problems.append("business rule: result does not match participants' home/away scores")
    return problems


def validate_against(schema_name: str, instance: dict) -> list:
    """Generic schema-only validation for models with no extra business rule."""
    return _schema_errors(instance, build_validator(schema_name))
