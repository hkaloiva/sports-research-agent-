# Validation

## Schema + business rule

`sports_research/validation/schema_validation.py`, `validate_event_result()`:
JSON Schema validation against `schema/event_result.schema.json`, plus
`event_result_matches_scores()` — the one cross-field rule the schema
can't express (score comparison for two-participant home/away events;
see `docs/data-model.md`). Same two-layer pattern Steps 2/4/5/6 already
established for every other model in this project.

## Duplicate detection

`sports_research/validation/dedup.py`, `group_duplicate_events()`.
Groups records by `(sport, competition, date, participant name set)` —
case/order-insensitive on names, but **no fuzzy matching** of spelling
variants. This is a deliberate precision-over-recall choice: merging two
records that are actually different events (because their names happened
to look similar) would be worse than occasionally missing a duplicate
whose team name was spelled differently between two sources.

## Cross-source verification

`sports_research/validation/conflicts.py`, `classify_group()`. Applied to
each group `dedup.py` found. Four possible outcomes:

| `verification_status` | When |
|---|---|
| `unverified` | Only one source, or 2+ sources but all from the *same* domain (not independent) |
| `verified` | 2+ *different-domain* sources, and they agree on every participant's score/placement and the top-level `result` |
| `conflicting` | 2+ sources disagree — **both claims are preserved** (nothing overwritten); the report lists exactly which sources said what |
| `disputed` | Reserved in the schema for a historical record that's genuinely contested independent of this pipeline's own sourcing — not currently set by any code path (no such case has arisen in this build's testing) |

Never marks a record `verified` from a single source, no matter how
credible that source looks — matching Step 7's `verification_status`
honesty requirement, generalized across the whole system.

## Completeness

`sports_research/validation/completeness.py`, `check_completeness()`.
`missing` is only ever a number when an `expected_count` is supplied —
currently, the only source of that is `planner.py`'s documented
Premier-League-38-games-per-club rule (Step 5). Every other request
reports `expected: None` / `missing: "unknown"` rather than a guessed
figure.

## What's *not* implemented

- No fuzzy/approximate duplicate matching (documented above as
  deliberate, not accidental).
- No `disputed` classification logic (the schema value exists; nothing
  currently sets it).
- No expected-count rules beyond the one inherited from Step 5's
  planner — most competitions report `missing: unknown`.

See `docs/limitations.md` for the full list.
