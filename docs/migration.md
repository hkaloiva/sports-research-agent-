# Migration: result_record → EventResult, and the ResearchRequest extension

Two schema changes were made building the standalone application, both
additive/backward-compatible.

## 1. `result_record.schema.json` → `event_result.schema.json`

**Not a breaking replacement** — `result_record.schema.json` and its
consumers (`validation.py`, `data/raw/test_results.json`,
`schema/examples/`) are untouched and still work exactly as before.
`event_result.schema.json` is a new, separate schema; `sports_research`'s
new code uses it, existing code keeps using the old one.

**Mapping** (`sports_research/models/migration.py`,
`migrate_result_record_to_event_result()`):

| result_record | event_result |
|---|---|
| `event_id`, `sport`, `competition`, `season`, `date`, `status`, `result`, `source`, `source_url`, `source_accessed_at`, `verification_status` | same field, same value |
| `round`, `notes` | same field, same value, still optional |
| `venue` | `location` (renamed; same shape) |
| `home_team`, `home_score` | `participants[0] = {name: home_team, role: "home", score: home_score}` |
| `away_team`, `away_score` | `participants[1] = {name: away_team, role: "away", score: away_score}` |

Deterministic, lossless, never invents a value — an absent field in the
input stays absent in the output. Tested in
`tests/sports_research/models/test_migration.py` against every record in
`data/raw/test_results.json` (Step 3's 20-record dataset), confirming
every migrated record validates against `event_result.schema.json`.

## 2. `research_request.schema.json`: added `event_name`

One new optional constraint field, `event_name`, alongside the existing
`sport`/`competition`/`season`/`teams`/etc. — needed for
individual/motorsport requests where "teams" doesn't apply (e.g.
"Wimbledon **Men's Singles**" or a specific Grand Prix name). Same
envelope shape (`value`/`source`/`basis?`/`raw_value?`) as every other
constraint field.

**Backward compatible**: all 5 of Step 4's original example
ResearchRequests (none of which use `event_name`) still validate
unchanged — verified directly (`validate_request()` against each,
confirmed empty problem lists) before this was committed.

## Why `teams`/`home_away` weren't renamed

`ResearchRequest.constraints.teams` is just an array of participant name
strings — it works identically whether the strings are football club
names or tennis players' names. Renaming it to `participants` would have
been a cosmetic API-ergonomics improvement, not a structural requirement,
and would have broken every existing example/test for no functional
gain. Documented here as a known, deliberate naming choice — see
`docs/limitations.md`.
