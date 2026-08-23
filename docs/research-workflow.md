# Research Workflow

What each pipeline stage (see `docs/architecture.md`) actually does,
via `sports_research/research/engine.py`'s `ResearchEngine.run()`.

## 1. Request normalization

`sports_research/research/normalizer.py`, `normalize_request()`.
Deterministic, rule-based (regex + small lookup tables) — **not** an LLM,
matching the zero-cost-mandatory requirement. Recognizes a small,
documented set of competitions (football leagues/cups, Street League
Skateboarding, Wimbledon, Formula 1) and maps each to a sport; extracts
season expressions (`2003/04` → `2003-2004`, preserving the original in
`raw_value`), explicit date ranges (`from 2000 to 2025`), and candidate
participant names (splitting on "and"/"vs"/"," for head-to-head phrasing).

A hard-coded ambiguous-alias list (`united`, `city`, ...) triggers
`status: "needs_clarification"` rather than guessing which club — same
"never silently invent a critical constraint" rule Step 4 established.
See `docs/limitations.md` for this approach's real limits (it is not a
general NLU system).

## 2. Research plan

`sports_research/research/planner.py` re-exports the existing
`planner.py` (Step 5) unchanged — it was already sport-agnostic in
structure. One real gap was found and fixed while testing non-football
requests: a competition+season query with no named participant
(`"Formula 1 ... 1990 season"`) previously dropped the season from the
generated query text; `planner.py` gained a `competition and season`
branch to fix this.

## 3. Search

`sports_research/search/`. `SearchProvider.search(query)` returns raw
hits shaped exactly like `search.py`'s (Step 6) existing `backend`
callable contract, so `search.build_search_execution()` — exact-URL
dedup, `query_used` tracking, never-fabricate guarantees — is reused
unchanged rather than reimplemented. See `docs/search.md`.

## 4. Source ranking

`sports_research/research/ranking.py`, `rank_sources()`. Classifies each
result URL into a `source_type` (domain heuristics) and orders fetch
priority: structured statistical databases and official sources first,
news articles and generic listings last — matching the SOURCE
PRIORITISATION policy from `docs/web-access-options.md`/`docs/search.md`.

## 5. Content retrieval

`sports_research/retrieval/`. Only the top `MAX_SOURCES_TO_FETCH`
ranked URLs are actually fetched (default 5 — see `docs/configuration.md`).
See `docs/retrieval.md`.

## 6–7. Extraction and normalization

`sports_research/extraction/`. Two participants + numeric score →
two-participant strategy; no named team/competitor → placement strategy.
See `docs/extraction.md`.

## 8. Validation

`sports_research/validation/schema_validation.py`,
`validate_event_result()` — schema + the one business rule pure JSON
Schema can't express. Kept as a genuinely separate step from extraction
(same pattern Step 7 established): extraction never calls validation.

## 9. Deduplication

`sports_research/validation/dedup.py`, `group_duplicate_events()`.
Groups records sharing `(sport, competition, date, participant name
set)` — deliberately coarse (no fuzzy name matching), so it never risks
merging genuinely different events over a spelling variant.

## 10. Cross-source comparison

`sports_research/validation/conflicts.py`, `classify_group()`. Never
marks a record `verified` from a single source (`unverified`) or from
two same-domain pages (still `unverified` — not independent
corroboration); `verified` requires 2+ *different-domain* sources that
agree; on disagreement, both claims are preserved and the group is
marked `conflicting` — nothing is silently overwritten.

## 11. Completeness check

`sports_research/validation/completeness.py`, `check_completeness()`.
`missing` is only ever computed against a documented expected count
(e.g. `planner.py`'s Premier-League-38-games rule from Step 5) — with no
such rule, it's reported as `None`/"unknown", never guessed.

## 12. Report and export

`sports_research/reporting/report.py` renders a plain-text summary
listing sources, verification breakdown, conflicts, validation issues,
and completeness — always ending with an explicit "this is not a claim
of a complete dataset" statement. `sports_research/export/` writes
CSV/JSON/XLSX — see `docs/exports.md`.
