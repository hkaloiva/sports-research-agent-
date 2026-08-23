#!/usr/bin/env python3
"""Generate a SearchPlan from a ResearchRequest JSON file and print it.

Run: python3 scripts/plan_from_request.py schema/examples/research_requests/01_team_season.json

Performs no web search, scraping, or browser automation — this only
prints the deterministic plan (see docs/search-strategy.md).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planner import AmbiguousRequestError, build_search_plan  # noqa: E402
from validation import (  # noqa: E402
    build_plan_validator,
    build_request_validator,
    validate_plan,
    validate_request,
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: plan_from_request.py <research_request.json>", file=sys.stderr)
        return 2

    request = json.loads(Path(sys.argv[1]).read_text())

    request_problems = validate_request(request, build_request_validator())
    if request_problems:
        print("Input is not a valid ResearchRequest:", file=sys.stderr)
        for problem in request_problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    try:
        plan = build_search_plan(request)
    except AmbiguousRequestError as e:
        print(f"Cannot build a SearchPlan: {e}", file=sys.stderr)
        return 1

    plan_problems = validate_plan(plan, build_plan_validator())
    if plan_problems:
        print("Generated SearchPlan failed its own schema (this would be a bug):", file=sys.stderr)
        for problem in plan_problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
