"""Deterministic SearchPlan generator.

Converts a 'ready' ResearchRequest (see schema/research_request.schema.json)
into a SearchPlan (see schema/search_plan.schema.json). This module does
NOT perform any web search, scraping, or browser automation, and it must
never claim that a source exists or that a query has produced results —
it only produces a plan for a research step that doesn't exist yet.

See docs/search-strategy.md for the full rationale behind every decision
made here.
"""

import hashlib
import json

# Fields carried from ResearchRequest.constraints into SearchPlan.search_scope,
# verbatim (same envelope: value/source/basis?/raw_value?) — this is how
# explicit vs. inferred provenance survives into the plan unchanged.
SCOPE_FIELDS = (
    "sport", "competition", "season", "date_from", "date_to",
    "teams", "venue", "home_away", "result_types",
)

# Fields eligible for cross-checking against a second source. Restricted to
# the ones most likely to be wrong/disputed in a historical record.
CORE_CROSS_CHECK_FIELDS = ("date", "home_team", "away_team", "home_score", "away_score", "result")

# Ordered most-preferred-first. See docs/search-strategy.md § source_types
# for the rationale (structured, purpose-built historical-result sources
# are preferred over narrative coverage when the objective is a dataset).
SOURCE_TYPES = (
    "statistical_database",
    "official_competition_source",
    "official_club_source",
    "sports_reference_site",
    "news_article",
    "search_engine_result",
)

PREFERRED_SOURCE_CHARACTERISTICS = (
    "Structured, tabular historical results (exact scores, dates) rather than narrative summaries",
    "Covers full-season archives, not just recent/current-season data",
    "Is itself an authoritative/official record, or explicitly cites one",
    "Independently corroborated by more than one outlet",
    "Includes explicit provenance (publish/update date, source attribution) so source and source_accessed_at can be populated accurately",
)

# The one domain-knowledge rule currently implemented for expected_result_count:
# the Premier League has been a 20-club, 38-match-per-club league every season
# since it moved to 20 clubs in 1995-96. No other competition/rule is
# implemented — anything else is correctly left unestimated rather than guessed.
PREMIER_LEAGUE_MATCHES_PER_CLUB_PER_SEASON = 38
PREMIER_LEAGUE_38_GAME_ERA_START_YEAR = 1995


class AmbiguousRequestError(ValueError):
    """Raised when asked to plan a ResearchRequest that isn't 'ready'."""


def compute_request_id(request: dict) -> str:
    """Content fingerprint of the request.

    ResearchRequest (Step 4) has no id field of its own — adding one was
    judged not worth modifying that schema for, since a deterministic
    hash of the request's own content gives the same guarantee (same
    request -> same id) without touching schema/research_request.schema.json.
    """
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _value(constraints: dict, field: str):
    entry = constraints.get(field)
    return entry["value"] if entry else None


def _season_years(season: str) -> tuple:
    """('2003-2004', '2003/04') -> (2003, 2004); ('2018', '2018/..') -> (2018, None)."""
    if "-" in season:
        start, end = season.split("-")
        return int(start), int(end)
    return int(season), None


def _season_slash(season: str) -> str:
    """'2003-2004' -> '2003/04'; '2018' -> '2018' (single-year seasons unchanged)."""
    start, end = _season_years(season)
    if end is None:
        return str(start)
    return f"{start}/{str(end)[-2:]}"


def _season_hyphen_short(season: str) -> str:
    """'2003-2004' -> '2003-04'; '2018' -> '2018'."""
    start, end = _season_years(season)
    if end is None:
        return str(start)
    return f"{start}-{str(end)[-2:]}"


def _is_premier_league_38_game_era(season: str) -> bool:
    start_year, _ = _season_years(season)
    return start_year >= PREMIER_LEAGUE_38_GAME_ERA_START_YEAR


def build_search_queries(constraints: dict) -> list:
    """Template-based query generation, branching on which constraints are
    present. Deliberately not a fixed list of literal strings — different
    inputs take different branches and produce different queries."""
    teams = _value(constraints, "teams")
    competition = _value(constraints, "competition")
    season = _value(constraints, "season")
    date_from = _value(constraints, "date_from")
    date_to = _value(constraints, "date_to")
    result_types = _value(constraints, "result_types")
    home_away = _value(constraints, "home_away")

    queries = []

    if teams and len(teams) == 1 and competition and season:
        team = teams[0]
        slash = _season_slash(season)
        hyphen_short = _season_hyphen_short(season)
        start_year, end_year = _season_years(season)

        queries.append({
            "query": f"{team} {slash} {competition} results",
            "rationale": "Direct team + season (slash form) + competition phrasing.",
        })
        if end_year is not None:
            queries.append({
                "query": f"{team} fixtures results {start_year} {end_year} {competition}",
                "rationale": "Both calendar years spelled out, for sources indexed by year rather than season label.",
            })
        else:
            queries.append({
                "query": f"{team} fixtures results {start_year} {competition}",
                "rationale": "Calendar year spelled out, for sources indexed by year rather than season label.",
            })
        queries.append({
            "query": f"{team} {hyphen_short} match results",
            "rationale": "Compact hyphenated season form, common in reference-site URLs and search indexes.",
        })
        queries.append({
            "query": f"historical {competition} {team} {slash} results",
            "rationale": "Leads with 'historical' and the competition name to bias toward archive/reference sources over recent news.",
        })
        if result_types:
            outcome_words = " and ".join(result_types)
            qualifier = f"{home_away} " if home_away else ""
            queries.append({
                "query": f"{team} {qualifier}{outcome_words} {competition} {slash}",
                "rationale": "Adds the requested result-type / home-away filter directly into the phrasing.",
            })

    elif teams and len(teams) == 2:
        t1, t2 = teams
        comp_suffix = f" {competition}" if competition else " all competitions"
        queries.append({
            "query": f"{t1} vs {t2}{comp_suffix} results",
            "rationale": "Most common natural head-to-head search phrasing.",
        })
        queries.append({
            "query": f"{t1} {t2} head to head{comp_suffix} all matches",
            "rationale": "'Head to head' is a common page-title/section phrase on stats sites.",
        })
        queries.append({
            "query": f"{t1} v {t2} results history{comp_suffix}",
            "rationale": "British-style 'v' abbreviation with 'history', another common indexing pattern.",
        })

    elif competition and (date_from or date_to):
        range_text = f"{date_from or '?'} to {date_to or '?'}"
        queries.append({
            "query": f"{competition} results {range_text}",
            "rationale": "Direct competition + explicit date range phrasing.",
        })
        if date_from and date_to:
            queries.append({
                "query": f"{competition} match results {date_from[:4]} {date_to[:4]}",
                "rationale": "Calendar-year form of the same range, for year-indexed sources.",
            })
        queries.append({
            "query": f"{competition} full results archive {date_from or ''}".strip(),
            "rationale": "Archive-oriented phrasing to bias toward structured historical listings over news.",
        })

    elif teams and len(teams) == 1 and season:
        # A real gap found via a live query ("All results Newcastle United
        # season 2000/2001" — team + season, no recognized competition
        # name): this used to fall straight through to the no-season
        # fallback below and silently drop the season from every
        # generated query, biasing search results toward the *current*
        # season instead of the requested one.
        team = teams[0]
        slash = _season_slash(season)
        hyphen_short = _season_hyphen_short(season)
        start_year, end_year = _season_years(season)

        queries.append({
            "query": f"{team} {slash} results",
            "rationale": "Direct team + season (slash form) phrasing; no competition name was recognized.",
        })
        if end_year is not None:
            queries.append({
                "query": f"{team} fixtures results {start_year} {end_year}",
                "rationale": "Both calendar years spelled out, for sources indexed by year rather than season label.",
            })
        else:
            queries.append({
                "query": f"{team} fixtures results {start_year}",
                "rationale": "Calendar year spelled out, for sources indexed by year rather than season label.",
            })
        queries.append({
            "query": f"{team} {hyphen_short} match results",
            "rationale": "Compact hyphenated season form, common in reference-site URLs and search indexes.",
        })
        queries.append({
            "query": f"historical {team} {slash} results",
            "rationale": "Leads with 'historical' to bias toward archive/reference sources over recent news.",
        })

    elif teams and len(teams) == 1:
        team = teams[0]
        comp_suffix = f" {competition}" if competition else ""
        queries.append({
            "query": f"{team}{comp_suffix} match results history",
            "rationale": "Generic single-team fallback when no season/date range narrows the request.",
        })
        queries.append({
            "query": f"{team}{comp_suffix} all-time results archive",
            "rationale": "Archive-oriented phrasing to bias toward structured historical listings.",
        })

    elif competition and season:
        start_year, end_year = _season_years(season)
        queries.append({
            "query": f"{competition} {season} results",
            "rationale": "Competition + season, no specific participant narrows the request further (e.g. a whole season/tournament of results).",
        })
        if end_year is not None:
            queries.append({
                "query": f"{competition} results {start_year} {end_year}",
                "rationale": "Calendar-year form of the season, for sources indexed by year rather than a season label.",
            })
        else:
            queries.append({
                "query": f"{competition} {start_year} results",
                "rationale": "Single-year season phrasing.",
            })
        queries.append({
            "query": f"{competition} {season} historical results archive",
            "rationale": "Archive-oriented phrasing to bias toward structured historical listings.",
        })

    elif competition:
        queries.append({
            "query": f"{competition} results",
            "rationale": "Generic competition-only fallback when no team, season, or date range narrows the request.",
        })
        queries.append({
            "query": f"{competition} historical results archive",
            "rationale": "Archive-oriented phrasing to bias toward structured historical listings.",
        })

    else:
        # Last-resort fallback: combine whatever scope is available at all.
        parts = [p for p in (teams[0] if teams else None, competition, season) if p]
        query_text = (" ".join(parts) + " results").strip() if parts else "results"
        queries.append({
            "query": query_text,
            "rationale": "Minimal fallback combining whatever scope is available; no team/season/competition/date-range branch matched.",
        })

    return queries


def build_search_scope(constraints: dict) -> dict:
    """Project the scope-relevant constraint envelopes straight through,
    unchanged, so explicit-vs-inferred provenance survives into the plan."""
    return {field: constraints[field] for field in SCOPE_FIELDS if field in constraints}


def build_expected_result_count(constraints: dict):
    """Returns an estimate dict, or None when no documented rule applies.
    Never a claim that any source/query has actually produced this many
    results — see schema/search_plan.schema.json's description."""
    teams = _value(constraints, "teams")
    competition = _value(constraints, "competition")
    season = _value(constraints, "season")

    if competition == "Premier League" and teams and len(teams) == 1 and season:
        if _is_premier_league_38_game_era(season):
            return {
                "value": PREMIER_LEAGUE_MATCHES_PER_CLUB_PER_SEASON,
                "basis": (
                    f"The Premier League has been a 20-club league, in which each club plays "
                    f"{PREMIER_LEAGUE_MATCHES_PER_CLUB_PER_SEASON} matches per season (home and away "
                    f"against every other club), every season since {PREMIER_LEAGUE_38_GAME_ERA_START_YEAR}-"
                    f"{PREMIER_LEAGUE_38_GAME_ERA_START_YEAR + 1}; season '{season}' falls within that era. "
                    "This is an estimate of how many matching records the plan expects to find, based on "
                    "known competition structure — not a claim that any source or query has been run."
                ),
            }
    return None


def build_pagination_strategy(constraints: dict) -> dict:
    bounded = ("season" in constraints) or ("date_from" in constraints and "date_to" in constraints)
    if bounded:
        return {
            "approach": "bounded_range_lookup",
            "max_pages_per_source": 3,
            "notes": (
                "Scope is bounded by a season or an explicit date range, so the relevant archive "
                "page(s) on a given source are expected to be limited; a small page cap is a reasonable "
                "starting heuristic, not a claim about any specific source's actual page count."
            ),
        }
    return {
        "approach": "iterative_unbounded_lookup",
        "max_pages_per_source": 10,
        "notes": (
            "No season or date range bounds this request (e.g. an all-time head-to-head), so matching "
            "records may span many years/archive pages; a higher page cap is used as a starting heuristic."
        ),
    }


def build_verification_strategy(constraints: dict) -> dict:
    verification = _value(constraints, "verification")
    required_fields = _value(constraints, "required_fields") or list(CORE_CROSS_CHECK_FIELDS)
    fields_to_cross_check = [f for f in CORE_CROSS_CHECK_FIELDS if f in required_fields]
    if not fields_to_cross_check:
        fields_to_cross_check = list(CORE_CROSS_CHECK_FIELDS)

    return {
        "requires_second_source": verification == "required",
        "fields_to_cross_check": fields_to_cross_check,
        "on_disagreement": "prefer_official_source_else_mark_conflicting",
        "notes": (
            "Default deterministic policy: prefer an official_competition_source or "
            "official_club_source among the disagreeing sources if one is present; otherwise leave "
            "the record's verification_status as 'conflicting' (result_record.schema.json) rather than "
            "silently picking a value. See docs/search-strategy.md § verification_strategy."
        ),
    }


def build_search_plan(request: dict) -> dict:
    """Build a SearchPlan from a ResearchRequest. Raises AmbiguousRequestError
    if the request's status isn't 'ready' — an ambiguous request must be
    resolved (clarifications_needed answered) before it can be planned;
    guessing at a plan for it would be exactly the silent invention this
    whole project is trying to avoid."""
    if request.get("status") != "ready":
        raise AmbiguousRequestError(
            "Cannot build a SearchPlan: ResearchRequest.status is "
            f"{request.get('status')!r}, not 'ready'. Resolve clarifications_needed first."
        )

    constraints = request["constraints"]

    plan = {
        "schema_version": "1.0.0",
        "research_request_id": compute_request_id(request),
        "search_queries": build_search_queries(constraints),
        "source_types": list(SOURCE_TYPES),
        "preferred_source_characteristics": list(PREFERRED_SOURCE_CHARACTERISTICS),
        "search_scope": build_search_scope(constraints),
        "pagination_strategy": build_pagination_strategy(constraints),
        "verification_strategy": build_verification_strategy(constraints),
    }

    expected_result_count = build_expected_result_count(constraints)
    if expected_result_count is not None:
        plan["expected_result_count"] = expected_result_count

    return plan
