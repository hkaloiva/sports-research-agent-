"""Shared schema-validation helpers used by scripts/ and tests/.

Factored out so the JSON Schema loading and the one business rule JSON
Schema can't express for result records (result must match the
home_score/away_score comparison) live in exactly one place. Research
requests have no equivalent Python-level rule — every cross-field rule
there (status vs. clarifications_needed, source vs. basis) is plain
value/enum logic that JSON Schema's if/then can express directly.
"""

import json

from jsonschema import Draft202012Validator, FormatChecker

from config import BASE_DIR

SCHEMA_PATH = BASE_DIR / "schema" / "result_record.schema.json"
REQUEST_SCHEMA_PATH = BASE_DIR / "schema" / "research_request.schema.json"
PLAN_SCHEMA_PATH = BASE_DIR / "schema" / "search_plan.schema.json"
SEARCH_RESULT_SCHEMA_PATH = BASE_DIR / "schema" / "search_result.schema.json"


def _schema_errors(instance: dict, validator: Draft202012Validator) -> list:
    return [
        f"schema: {e.message} (at {'/'.join(str(p) for p in e.path) or '(root)'})"
        for e in validator.iter_errors(instance)
    ]


def _build_validator(schema_path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def build_validator() -> Draft202012Validator:
    return _build_validator(SCHEMA_PATH)


def load_request_schema() -> dict:
    return json.loads(REQUEST_SCHEMA_PATH.read_text())


def build_request_validator() -> Draft202012Validator:
    return _build_validator(REQUEST_SCHEMA_PATH)


def validate_request(request: dict, validator: Draft202012Validator) -> list:
    """Return a list of problem strings; an empty list means fully valid.

    Unlike validate_record(), no extra Python-level business rule is
    needed — the request schema's cross-field rules are all plain
    value/enum comparisons, fully expressible in JSON Schema itself.
    """
    return _schema_errors(request, validator)


def load_plan_schema() -> dict:
    return json.loads(PLAN_SCHEMA_PATH.read_text())


def build_plan_validator() -> Draft202012Validator:
    return _build_validator(PLAN_SCHEMA_PATH)


def validate_plan(plan: dict, validator: Draft202012Validator) -> list:
    """Return a list of problem strings; an empty list means fully valid.

    Like validate_request(), no extra Python-level business rule is
    needed — the plan schema's cross-field rules are all plain
    value/enum comparisons, fully expressible in JSON Schema itself.
    """
    return _schema_errors(plan, validator)


def load_search_result_schema() -> dict:
    return json.loads(SEARCH_RESULT_SCHEMA_PATH.read_text())


def build_search_result_validator() -> Draft202012Validator:
    return _build_validator(SEARCH_RESULT_SCHEMA_PATH)


def validate_search_result(item: dict, validator: Draft202012Validator) -> list:
    """Return a list of problem strings; an empty list means fully valid.

    No extra Python-level business rule is needed here either — every
    constraint on a SearchResult is a plain type/format check.
    """
    return _schema_errors(item, validator)


def result_matches_scores(record: dict) -> bool:
    """The one cross-field rule JSON Schema can't express: result must
    match the comparison of home_score vs away_score."""
    status = record.get("status")
    home = record.get("home_score")
    away = record.get("away_score")
    result = record.get("result")

    if status in ("scheduled", "postponed", "cancelled"):
        return result is None
    if status == "abandoned":
        return result in (None, "void")
    if status == "completed":
        if isinstance(home, int) and isinstance(away, int):
            if home > away:
                return result == "home_win"
            if away > home:
                return result == "away_win"
            return result == "draw"
        return result == "unknown"
    return True


def validate_record(record: dict, validator: Draft202012Validator) -> list:
    """Return a list of problem strings; an empty list means fully valid."""
    problems = _schema_errors(record, validator)
    if not result_matches_scores(record):
        problems.append("business rule: result does not match status/home_score/away_score")
    return problems
