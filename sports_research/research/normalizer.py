"""Natural-language ResearchRequest normalizer.

Deterministic, rule-based (regex + small lookup tables) — NOT a general
NLU system, and does not require any LLM (matches the zero-cost-mandatory
requirement). Builds a ResearchRequest exactly per
schema/research_request.schema.json (Step 4, reused unchanged): every
constraint is either "explicit" (found directly in the text, possibly
reformatted) or "inferred" (with a documented basis), and anything this
rule set can't confidently resolve becomes a clarification requirement
rather than a guess. See docs/research-workflow.md § Request
normalization for the honest scope/limits of this approach.
"""

import re

# competition phrase -> (canonical name, sport). Longest-phrase-first
# matching below, so 'uefa champions league' beats a plainer alias.
_COMPETITIONS = [
    ("uefa champions league", "UEFA Champions League", "football"),
    ("champions league", "UEFA Champions League", "football"),
    ("premier league", "Premier League", "football"),
    ("fifa world cup", "FIFA World Cup", "football"),
    ("world cup", "FIFA World Cup", "football"),
    ("la liga", "La Liga", "football"),
    ("fa cup", "FA Cup", "football"),
    ("uefa european championship", "UEFA European Championship", "football"),
    ("euro", "UEFA European Championship", "football"),
    ("copa américa", "Copa América", "football"),
    ("copa america", "Copa América", "football"),
    ("street league skateboarding", "Street League Skateboarding", "skateboarding"),
    ("sls", "Street League Skateboarding", "skateboarding"),
    ("wimbledon", "Wimbledon", "tennis"),
    ("formula 1", "Formula 1", "motorsport"),
    ("formula one", "Formula 1", "motorsport"),
    ("f1", "Formula 1", "motorsport"),
]

# Ambiguous single-word club/team names that must not be silently resolved.
_AMBIGUOUS_TEAM_ALIASES = {
    "united": ["Manchester United", "Newcastle United", "West Ham United", "Leeds United"],
    "city": ["Manchester City", "Leicester City", "Stoke City"],
}

_STOPWORDS = {
    "find", "all", "every", "results", "result", "of", "the", "from", "season", "match",
    "matches", "a", "an", "for", "show", "me", "list", "get", "please", "and", "to",
    "how", "who", "what", "when", "where", "why", "which", "did", "does", "do", "have",
    "has", "against", "each", "other", "in", "done",
}

_COORDINATORS = re.compile(r"\s*(?:,|\band\b|\bvs\.?\b|\bv\b)\s*", re.IGNORECASE)

_EVENT_NAME_PATTERNS = [
    (re.compile(r"\bmen'?s singles\b", re.I), "Men's Singles"),
    (re.compile(r"\bwomen'?s singles\b", re.I), "Women's Singles"),
    (re.compile(r"\bmen'?s doubles\b", re.I), "Men's Doubles"),
    (re.compile(r"\bwomen'?s doubles\b", re.I), "Women's Doubles"),
]


def _find_competition(text_lower: str):
    for phrase, canonical, sport in _COMPETITIONS:
        if phrase in text_lower:
            return phrase, canonical, sport
    return None


def _find_season(text: str):
    """Returns (raw_text, canonical) for a season expression, or None."""
    match = re.search(r"\b(\d{4})\s*/\s*(\d{2})\b", text)  # '2003/04'
    if match:
        start = int(match.group(1))
        end_suffix = match.group(2)
        end = int(str(start)[:2] + end_suffix)
        return match.group(0), f"{start}-{end}"

    match = re.search(r"\b(\d{4})-(\d{4})\b", text)  # '2003-2004'
    if match:
        return match.group(0), f"{match.group(1)}-{match.group(2)}"

    return None


def _find_date_range(text: str):
    match = re.search(r"\bfrom\s+(\d{4})\s+to\s+(\d{4})\b", text, re.I)
    if match:
        return f"{match.group(1)}-01-01", f"{match.group(2)}-12-31", match.group(0)
    return None


def _find_bare_year(text: str):
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return match.group(0) if match else None


def _find_event_name(text: str):
    for pattern, canonical in _EVENT_NAME_PATTERNS:
        if pattern.search(text):
            return canonical
    return None


def _strip_span(text: str, phrase: str) -> str:
    """Case-insensitively remove the first occurrence of `phrase` from
    `text`, so it's never mistaken for a participant name."""
    if not phrase:
        return text
    pattern = re.compile(re.escape(phrase), re.IGNORECASE)
    return pattern.sub(" ", text, count=1)


def _find_candidate_participants(text: str) -> list:
    """Best-effort: capitalized word run(s) left in `text` after the
    competition phrase, event-name phrase, season/date expressions, and
    stopwords have already been stripped out by the caller. Splits on
    'and'/','/'vs'/'v' so head-to-head phrasing ('Liverpool and Everton')
    produces two separate participants rather than one joined string —
    a real, documented limitation of this rule-based approach is that it
    still can't tell a two-word team name ('Manchester United') from two
    separate one-word participants without a lookup list; see
    docs/research-workflow.md."""
    participants = []
    for segment in _COORDINATORS.split(text):
        words = re.findall(r"[A-Za-z][A-Za-z]*", segment)
        candidate_words = [w for w in words if w.lower() not in _STOPWORDS and w[0].isupper()]
        if candidate_words:
            participants.append(" ".join(candidate_words))
    return participants


def normalize_request(raw_query: str) -> dict:
    """Build a ResearchRequest dict (schema/research_request.schema.json).
    Never invents a constraint the text doesn't support — an unresolved
    ambiguity (unknown team alias, no competition/participant found at
    all) produces status='needs_clarification' instead."""
    text_lower = raw_query.lower()
    constraints = {}
    clarifications = []

    competition_match = _find_competition(text_lower)
    if competition_match:
        phrase, canonical, sport = competition_match
        constraints["competition"] = {"value": canonical, "source": "explicit"}
        constraints["sport"] = {
            "value": sport, "source": "inferred",
            "basis": f"Entailed by the explicitly stated competition '{canonical}'.",
        }

    date_range = _find_date_range(raw_query)
    season_match = _find_season(raw_query)
    if date_range:
        date_from, date_to, raw_text = date_range
        constraints["date_from"] = {"value": date_from, "source": "explicit", "raw_value": raw_text}
        constraints["date_to"] = {"value": date_to, "source": "explicit", "raw_value": raw_text}
    elif season_match:
        raw_text, canonical = season_match
        constraints["season"] = {"value": canonical, "source": "explicit", "raw_value": raw_text}
    else:
        bare_year = _find_bare_year(raw_query)
        if bare_year:
            constraints["season"] = {"value": bare_year, "source": "explicit"}

    event_name = _find_event_name(raw_query)
    if event_name:
        constraints["event_name"] = {"value": event_name, "source": "explicit"}

    remaining_text = raw_query
    if competition_match:
        remaining_text = _strip_span(remaining_text, competition_match[0])
    if date_range:
        remaining_text = _strip_span(remaining_text, date_range[2])
    elif season_match:
        remaining_text = _strip_span(remaining_text, season_match[0])
    for pattern, _ in _EVENT_NAME_PATTERNS:
        remaining_text = pattern.sub(" ", remaining_text)

    candidates = _find_candidate_participants(remaining_text)
    ambiguous_hit = next((c for c in candidates if c.lower() in _AMBIGUOUS_TEAM_ALIASES), None)
    if ambiguous_hit:
        options = _AMBIGUOUS_TEAM_ALIASES[ambiguous_hit.lower()]
        clarifications.append({
            "field": "teams",
            "question": f"Which club named '{ambiguous_hit}' do you mean — e.g. {', '.join(options)}?",
            "reason": f"'{ambiguous_hit}' matches multiple well-known clubs; the request does not disambiguate which one.",
        })
    elif candidates:
        constraints["teams"] = {"value": candidates, "source": "explicit"}

    if "last season" in text_lower or "this season" in text_lower:
        clarifications.append({
            "field": "season",
            "question": "Which season do you mean? Please give an explicit season, e.g. '2023-2024'.",
            "reason": "A relative season reference ('last/this season') has no documented rule for resolving to a concrete season.",
        })
        constraints.pop("season", None)

    if not competition_match and "sport" not in constraints:
        clarifications.append({
            "field": "sport",
            "question": "Which sport or competition is this about?",
            "reason": "No recognized sport or competition name was found in the request.",
        })

    if "required_fields" not in constraints:
        constraints["required_fields"] = {
            "value": ["date", "home_team", "away_team", "home_score", "away_score", "result"],
            "source": "inferred",
            "basis": "Default core-outcome field set when unspecified.",
        }
    if "verification" not in constraints:
        constraints["verification"] = {
            "value": "required", "source": "inferred",
            "basis": "Default verification requirement when unspecified.",
        }
    if "output_format" not in constraints:
        constraints["output_format"] = {
            "value": "json", "source": "inferred",
            "basis": "Default output format when unspecified.",
        }

    status = "needs_clarification" if clarifications else "ready"
    return {
        "schema_version": "1.0.0",
        "raw_query": raw_query,
        "status": status,
        "constraints": constraints,
        "clarifications_needed": clarifications,
    }
