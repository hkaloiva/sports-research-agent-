"""Completeness check: expected vs. found event counts.

Never invents missing events to satisfy an expected count — this only
reports the gap for a human to see.
"""


def check_completeness(found_count: int, duplicate_count: int, unresolved_count: int, expected_count: int = None) -> dict:
    """expected_count is optional (e.g. from a documented competition-
    structure rule, mirroring planner.py's Premier-League-38-games rule
    from Step 5) — when it's None, `missing` is also None rather than a
    guessed number."""
    result = {
        "expected": expected_count,
        "found": found_count,
        "duplicate": duplicate_count,
        "unresolved": unresolved_count,
        "missing": None,
    }
    if expected_count is not None:
        result["missing"] = max(expected_count - found_count, 0)
    return result
