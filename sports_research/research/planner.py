"""Re-exports Step 5's planner.py (ResearchRequest -> SearchPlan) under
the sports_research.research namespace. Not reimplemented here — that
module was already designed sport-agnostically (it works off generic
`teams`/`competition`/`season`/`date_from`/`date_to` fields, not
football-specific ones) and this build's testing confirmed it generalizes
correctly to skateboarding/motorsport/tennis requests (after one real gap
was fixed: a competition+season-with-no-participant query previously
dropped the season from the generated query text — see the top-level
planner.py's new 'elif competition and season' branch)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from planner import AmbiguousRequestError, build_search_plan  # noqa: E402,F401
