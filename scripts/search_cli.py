#!/usr/bin/env python3
"""Execute a ResearchRequest's SearchPlan and print structured SearchResults.

    python3 scripts/search_cli.py <research_request.json> --backend-fixture <raw_hits.json> [--provider NAME] [--out out.json]

<raw_hits.json> is a {query: [ {"title": ..., "url": ..., "snippet": ...}, ... ]}
mapping — real search-provider output (see docs/search-module.md for why
this module takes results as data rather than embedding a search client).

This performs no extraction of sports results and no CSV/Excel export —
only ResearchRequest -> SearchPlan -> SearchResult.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planner import AmbiguousRequestError, build_search_plan  # noqa: E402
from search import build_search_execution, prefetched_backend_from_file  # noqa: E402
from validation import (  # noqa: E402
    build_plan_validator,
    build_request_validator,
    build_search_result_validator,
    validate_plan,
    validate_request,
    validate_search_result,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("research_request", type=Path, help="Path to a ResearchRequest JSON file.")
    parser.add_argument("--backend-fixture", type=Path, required=True, help="Path to a {query: [raw_hit, ...]} JSON file of real search-provider output.")
    parser.add_argument("--provider", default="claude_web_search", help="Name of the search backend that produced --backend-fixture.")
    parser.add_argument("--out", type=Path, help="Write the SearchExecution JSON here in addition to printing it.")
    args = parser.parse_args()

    request = json.loads(args.research_request.read_text())
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

    backend = prefetched_backend_from_file(args.backend_fixture)
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    execution = build_search_execution(plan, backend, provider=args.provider, retrieved_at=retrieved_at)

    result_validator = build_search_result_validator()
    for result in execution["results"]:
        problems = validate_search_result(result, result_validator)
        if problems:
            print(f"Generated SearchResult failed its own schema (this would be a bug) for {result.get('url')}:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1

    output = json.dumps(execution, indent=2)
    print(output)
    if args.out:
        args.out.write_text(output + "\n")
        print(f"\nAlso wrote {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
