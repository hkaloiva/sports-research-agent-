# Data Model

## EventResult (`schema/event_result.schema.json`)

The sport-generic canonical record. Successor to
`schema/result_record.schema.json` (Step 2), which only modeled football
(`home_team`/`away_team`/`home_score`/`away_score`). EventResult
generalizes "two teams with scores" into **N participants**, each with an
optional `score` and/or `placement`:

```json
{
  "event_id": "football:premier-league:2003-2004:2003-08-16:arsenal-vs-everton",
  "sport": "football",
  "competition": "Premier League",
  "season": "2003-2004",
  "date": "2003-08-16",
  "participants": [
    {"name": "Arsenal", "role": "home", "score": 2},
    {"name": "Everton", "role": "away", "score": 1}
  ],
  "status": "completed",
  "result": "home_win",
  "source": "...", "source_url": "...", "source_accessed_at": "...",
  "verification_status": "verified"
}
```

```json
{
  "event_id": "skateboarding:street-league-skateboarding:2015:2015-09-20:world-championship",
  "sport": "skateboarding",
  "competition": "Street League Skateboarding",
  "season": "2015",
  "event_name": "World Championship",
  "date": "2015-09-20",
  "participants": [
    {"name": "Nyjah Huston", "role": "competitor", "placement": 1, "score": 93.5},
    {"name": "Shane O'Neill", "role": "competitor", "placement": 2, "score": 88.2}
  ],
  "status": "completed",
  "result": "win"
}
```

Same record shape, same schema, same validation code
(`sports_research/validation/schema_validation.py`) — no football-only
assumption anywhere in the model.

### `role` vocabulary (documented, not schema-enforced)

`home`/`away` for two-side team sports; `competitor` for individual
sports; `driver` for motorsport. Open — a new sport can use a new role
without a schema change.

### The one business rule this schema still can't express generically

For exactly two participants with roles `home`/`away` and numeric scores,
`result` must match the score comparison
(`event_result_matches_scores()` in `validation/schema_validation.py`).
No equivalent rule exists for placement-based events — those rely on
`participants[].placement`, which nothing second-guesses.

## Source (`sports_research/models/source.py`)

Stored separately from EventResults (PROVENANCE in the build spec):
`source_id`, `title`, `url`, `domain`, `retrieved_at`, `retrieval_status`,
`source_type`. `source_type` is one of the categories from
`docs/search.md`'s source ranking, classified by
`sports_research/research/ranking.py`.

## ResearchRequest, SearchPlan, SearchResult

Unchanged from Steps 4–6 (`docs/research-request.md`,
`docs/search-strategy.md`, `docs/search-module.md`), with one additive
extension — see `docs/migration.md`. These were already sport-agnostic in
structure (their `teams`/`home_away` fields are just strings/enums that
work for any sport's participant names/roles), so no rewrite was needed;
only `event_name` was missing for individual/motorsport requests.

## See also

`docs/migration.md` for the full result_record → EventResult mapping and
the ResearchRequest schema extension.
