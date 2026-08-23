"""Migrate football-only result_record dicts (schema/result_record.schema.json,
Step 2) into sport-generic EventResult dicts (schema/event_result.schema.json).

See docs/migration.md for the full field-by-field mapping and rationale.
"""


def migrate_result_record_to_event_result(record: dict) -> dict:
    """Lossless, deterministic mapping — every result_record field has a
    clear home in EventResult. Never invents anything: fields absent in
    the input stay absent in the output."""
    participants = [
        {"name": record["home_team"], "role": "home", "score": record["home_score"]},
        {"name": record["away_team"], "role": "away", "score": record["away_score"]},
    ]

    event = {
        "schema_version": "1.0.0",
        "event_id": record["event_id"],
        "sport": record["sport"],
        "competition": record["competition"],
        "season": record["season"],
        "date": record["date"],
        "participants": participants,
        "status": record["status"],
        "result": record["result"],
        "source": record["source"],
        "source_url": record["source_url"],
        "source_accessed_at": record["source_accessed_at"],
        "verification_status": record["verification_status"],
    }
    if "round" in record:
        event["round"] = record["round"]
    if "venue" in record:
        event["location"] = record["venue"]
    if "notes" in record:
        event["notes"] = record["notes"]
    return event
