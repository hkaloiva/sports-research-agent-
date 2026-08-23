# Search Strategy — SearchPlan Model

This document explains `SearchPlan`: a deterministic plan for how a future
research step *would* look for information, generated from a `"ready"`
[`ResearchRequest`](research-request.md). It is still not the research
step itself — no web search, scraping, or browser automation happens
anywhere in this project yet. `SearchPlan` describes intent, not action.

The machine-readable schema is
[`schema/search_plan.schema.json`](../schema/search_plan.schema.json). The
generator is [`planner.py`](../planner.py) (`build_search_plan()`).

## The one hard rule: never claim a source exists or a query ran

Nothing in a `SearchPlan` may be read as "this source exists", "this URL
is real", or "this query returned N results". Concretely:

- `search_queries` are strings **to try**, not evidence anything was
  tried. No real domains or `site:` filters are embedded in the generated
  query text — which specific site to hit is a decision for the (not yet
  built) research step, not this planner.
- `expected_result_count`, where present, is explicitly framed in its own
  `basis` text as an *estimate from known competition structure* — see
  [Expected result count](#expected-result-count) below. It is omitted
  entirely, never guessed, whenever no such documented rule applies.
- `pagination_strategy.notes` explicitly calls its own approach a
  "heuristic starting point", not a measured fact about any real source.

Tests in `tests/test_search_plan.py`
(`TestPlannerDoesNotClaimResults`) check this framing directly, so it
doesn't quietly drift.

## Preserving three kinds of information

The prompt for this step asks for the distinction between *user-provided
constraints*, *inferred constraints*, and *strategy decisions* to survive
into the plan. Each lives in a different, clearly separated part of the
schema:

1. **User-provided / inferred constraints** → `search_scope`. This is a
   straight, unmodified copy of the relevant entries from the originating
   `ResearchRequest.constraints` — same envelope (`value`/`source`/
   `basis`/`raw_value`) as Step 4 defined. The planner does not
   re-derive or re-tag anything here; it only *selects* which of the
   request's constraints bound the search (see
   [`SCOPE_FIELDS`](../planner.py)) and passes them through byte-for-byte.
   A caller can always tell, for any scoped field, whether the user said
   it or the system inferred it (and why), because that's literally what
   was already recorded in the request.
2. **Strategy decisions** → everything else: `search_queries`,
   `source_types`, `preferred_source_characteristics`,
   `pagination_strategy`, `verification_strategy`. These are the
   planner's own choices about *how* to search, not restatements of what
   the user asked for. They're deterministic functions of the request's
   constraints, but they are not themselves user input or inferred user
   intent — mixing them into `search_scope` would blur exactly the
   distinction this step asks for.

## research_request_id

`ResearchRequest` (Step 4) has no id field of its own, and modifying that
schema wasn't judged necessary just to add one here. Instead,
`research_request_id` is a content fingerprint:
`"sha256:" + sha256(canonical_json(request)).hexdigest()`, where
`canonical_json` sorts keys and uses compact separators. The same request
content always produces the same id — useful for caching/dedup — without
touching `research_request.schema.json`.

## search_queries: a reusable strategy, not fixed strings

The prompt's own worked example (Arsenal, 2003/04, Premier League) lists
four illustrative query phrasings. Those exact strings are **not**
hard-coded anywhere in `planner.py`. Instead, `build_search_queries()`
branches on *which constraints are present* and fills query templates
from them, so the same logic produces sensibly different queries for
inputs the worked example never covers:

| When `search_scope` has... | Query templates used |
|---|---|
| one team + competition + season | direct "`{team} {season/slash} {competition} results`"; a fixtures/years variant spelling out both calendar years; a compact hyphenated-season variant; an "historical" -prefixed variant; plus one more incorporating `result_types`/`home_away` if present |
| exactly two teams | "`{t1} vs {t2} ... results`"; "`{t1} {t2} head to head ...`"; "`{t1} v {t2} results history ...`" |
| competition + a date range (no team) | range-phrased, calendar-year-phrased, and archive-phrased variants |
| one team, no season/competition | generic team-results and team-archive fallbacks |
| competition only | generic competition-results and competition-archive fallbacks |
| none of the above | a minimal fallback combining whatever scope exists |

Season strings are reformatted into the natural-language variants a
search engine query would actually use (`"2003-2004"` → `"2003/04"` and
`"2003-04"`, plus the bare years `2003`/`2004`) — this reformatting is
purely about query *text*, not a change to any canonical schema value, so
it doesn't interact with the `source: explicit`/`inferred` distinction at
all (that distinction lives in `search_scope`, not in query strings).

Every query carries a `rationale` explaining why that phrasing was
generated, so the strategy is auditable rather than a black box.

## source_types

Ordered, most-preferred-first, for the objective of *building a
structured dataset* (not "finding an article about it"):

1. `statistical_database` — purpose-built for exhaustive, structured
   historical results; the best fit for this objective specifically.
2. `official_competition_source` — authoritative, but historical-archive
   depth/searchability varies by competition.
3. `official_club_source` — authoritative for that club, same caveat.
4. `sports_reference_site` — similar strengths to a statistical database,
   kept as a distinct category per the brief.
5. `news_article` — narrative coverage; deprioritized on purpose, since a
   dataset needs facts, not summaries. Useful mainly for corroboration.
6. `search_engine_result` — not itself a source of facts; the mechanism
   for discovering candidates in the categories above.

This order is currently fixed (the same for every plan) since football is
the only sport this project supports. A future multi-sport version might
vary it per `sport`.

## preferred_source_characteristics

A fixed, deterministic list (`planner.PREFERRED_SOURCE_CHARACTERISTICS`)
describing the qualities a good source should have, independent of which
team/competition/season is being asked about: structured/tabular over
narrative, full-season archive coverage, authoritative or citing an
authority, independently corroborated, and carrying its own provenance
(so `source`/`source_accessed_at` on the eventual result record can be
filled in accurately).

## expected_result_count

The **only** domain-knowledge rule implemented right now:

> The Premier League has been a 20-club league in which each club plays
> 38 matches per season (home and away against every other club) every
> season since 1995-96.

When a plan's scope is exactly *one team + `"Premier League"` +
a `season`* that falls in that era, `expected_result_count` is
`{"value": 38, "basis": "..."}`. In every other case — a different
competition, no season, two teams, a date range instead of a season —
the field is simply **absent**. This mirrors the exact rule from Step 4:
no documented rule → no invented value, ever, not even an optimistic
guess.

## pagination_strategy

Two heuristic approaches, chosen by whether the scope is bounded:

- **`bounded_range_lookup`** (a `season` or an explicit `date_from`
  +`date_to` pair is in scope): a small page cap (3), since the relevant
  archive material for a bounded window is expected to be limited.
- **`iterative_unbounded_lookup`** (neither is present — e.g. an all-time
  head-to-head): a larger page cap (10), since matching records could
  span many years.

Both are explicitly framed as starting heuristics for a not-yet-built
research step, not measurements of any real source.

## verification_strategy

- **`requires_second_source`**: taken directly from the request's
  `verification` constraint (`"required"` → `true`). No independent
  inference here — this one strategy field is a direct pass-through of an
  explicit request setting.
- **`fields_to_cross_check`**: the intersection of the request's
  `required_fields` with the fields most likely to be wrong or disputed
  in a historical record — `date`, `home_team`, `away_team`, `home_score`,
  `away_score`, `result`. Fields the requester didn't ask for aren't
  cross-checked.
- **`on_disagreement`**: the planner's current deterministic default is
  `"prefer_official_source_else_mark_conflicting"` — if an
  `official_competition_source`/`official_club_source` is among the
  disagreeing sources, prefer it; otherwise leave the record's
  `verification_status` as `"conflicting"` (the exact value
  `result_record.schema.json` already defines for this — Step 2's
  vocabulary, reused here rather than reinvented) instead of silently
  picking one side. `"mark_conflicting_no_resolution"` and
  `"escalate_to_user"` remain valid schema values for future policies,
  just not the current default.

## Generating a plan

```bash
cd sports-research-agent
python3 scripts/plan_from_request.py schema/examples/research_requests/01_team_season.json
```

An ambiguous request (`status: "needs_clarification"`) raises
`planner.AmbiguousRequestError` instead of producing a plan — see
`schema/examples/research_requests/05_ambiguous_needs_clarification.json`.

## Running the tests

```bash
python3 -m unittest discover
```

`tests/test_search_plan.py` covers: team+competition+season,
head-to-head, competition+date-range, result-type filtering, the
ambiguous-request rejection, the no-claims framing, and that different
requests produce different query sets.
