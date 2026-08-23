# Historical Sports Result — Data Schema

This document explains the canonical record used to represent a single
historical sports result. The machine-readable version lives at
[`schema/result_record.schema.json`](../schema/result_record.schema.json)
(JSON Schema, draft 2020-12). Example records validated against it live in
[`schema/examples/`](../schema/examples/).

The schema is written football/soccer-first (it's the only sport the
pipeline populates today) but is deliberately kept sport-agnostic where
that costs nothing, so other sports can be added later without reshaping
existing records — see [Extensibility](#extensibility-to-other-sports)
below.

## Field reference

| Field | Type | Required | Allowed values / format | Notes |
|---|---|---|---|---|
| `schema_version` | string | No | `"1.0.0"` (currently the only value) | Assumed to be the current version if omitted. |
| `event_id` | string | **Yes** | any string, ≥3 chars | Stable unique ID. Recommended: `{sport}:{competition-slug}:{season}:{date}:{home-team-slug}-vs-{away-team-slug}`. A UUIDv4 is also fine. Must stay stable across re-runs so records can be de-duplicated/updated in place. |
| `sport` | string | **Yes** | lowercase `snake_case`, e.g. `football` | Only `football` is populated today; add new sports by using a new value, not by editing this field's definition. |
| `competition` | string | **Yes** | free text, non-empty | Full official name, used consistently (e.g. `Premier League`, not `PL` in one record and `EPL` in another). |
| `season` | string | **Yes** | `YYYY` or `YYYY-YYYY` | `YYYY` for single-calendar-year seasons (e.g. `2018` for a World Cup), `YYYY-YYYY` for seasons spanning a year boundary (e.g. `2023-2024` for most European league seasons). Never two-digit years (`23-24`). |
| `round` | string | No | free text, non-empty if present | E.g. `Matchday 5`, `Round of 16`, `Final`. Omit if not applicable/unknown. |
| `date` | string | **Yes** | ISO 8601 `date` or `date-time` | See [Dates](#dates) below. |
| `home_team` | string | **Yes** | free text, non-empty | See [Home/away on neutral venues](#homeaway-on-neutral-venues). |
| `away_team` | string | **Yes** | free text, non-empty | |
| `home_score` | integer or `null` | **Yes** (key always present) | integer ≥ 0, or `null` | See [Scores](#scores). |
| `away_score` | integer or `null` | **Yes** (key always present) | integer ≥ 0, or `null` | |
| `result` | string or `null` | **Yes** (key always present) | `home_win`, `draw`, `away_win`, `void`, `unknown`, or `null` | Derived from the scores — see [Result derivation](#result-derivation). |
| `venue` | object | No | `{name?, city?, country?}` | Whole object and every sub-field optional. |
| `status` | string | **Yes** | `scheduled`, `completed`, `postponed`, `cancelled`, `abandoned` | See [Status](#status). |
| `source` | string | **Yes** | free text, non-empty | Name of the source, e.g. `Wikipedia`, `BBC Sport`. |
| `source_url` | string | **Yes** | URI | Direct link to the page the data came from. |
| `source_accessed_at` | string | **Yes** | ISO 8601 date-time, with offset | When the source was *retrieved*, not when the event happened. |
| `verification_status` | string | **Yes** | `unverified`, `verified`, `conflicting`, `disputed` | See [Verification status](#verification-status). |
| `notes` | string | No | free text | Context on conflicts, oddities, resolution rationale, etc. |

`additionalProperties` is `false` — a record with a field not listed above
will fail validation. This is intentional at this stage; loosen it later
if a real need for arbitrary extra fields shows up.

### Required vs optional

Every field is required **except** `schema_version`, `round`, `venue`, and
`notes`. "Required" for `home_score`, `away_score`, and `result` means the
*key* must always be present — the *value* is allowed to be `null` (see
below). This is deliberate: a record that's missing these keys entirely
looks like an oversight, while a record with them explicitly `null`
documents "we checked, and there's no score/result here."

### Dates

All dates and timestamps use **ISO 8601**:

- Date-only, when only the day is known: `"2018-07-15"`.
- Full timestamp, when kickoff/start time is known: `"2018-07-15T18:00:00+03:00"`
  or `"2018-07-15T18:00:00Z"`. Always include a UTC offset — never a
  timezone-naive timestamp.

`date` accepts either form (the event's date/time itself is often only
known to day precision, especially for older results). `source_accessed_at`
is always a full timestamp, since it records when the pipeline ran, which
is always known precisely.

### Scores

- `home_score` and `away_score` are **separate integer fields**. A combined
  string like `"2-1"` is never used as the canonical representation —
  that's a display concern for a later export/formatting step, not how the
  data is stored.
- Both fields are always present as keys. Their value is a non-negative
  integer when the score is known, or `null` when it isn't (event not yet
  played, postponed, cancelled, abandoned before either team scored, or
  completed but genuinely unrecoverable — see the third example record).
- Nothing is ever invented here. If a score isn't confirmed, the field is
  `null`, not a guess, not `0`, and not omitted.

### Result derivation

`result` must be consistent with `status`, `home_score`, and `away_score`:

- `status: completed` with both scores known integers → `result` must be
  `home_win` (`home_score > away_score`), `away_win`
  (`away_score > home_score`), or `draw` (equal — only meaningful for
  sports where draws exist).
- `status: completed` with score(s) unavailable → `result` is `unknown`.
- `status: scheduled`, `postponed`, or `cancelled` → `home_score`,
  `away_score`, and `result` are all `null`. There is no result to derive
  because the event hasn't produced one.
- `status: abandoned` → no score is invented; `result` is `null` or `void`
  (`void` when the competition officially declares the fixture void/no
  contest).

**Implementation note:** JSON Schema can express "if `status` is
`postponed` then `result` must be `null`" (a value depends on another
value), but it cannot express "if `home_score` > `away_score` then
`result` must be `home_win`" — comparing two sibling property *values*
arithmetically is outside what JSON Schema's `if`/`then` can do. The
schema (`allOf` block) enforces every rule above **except** the score
comparison itself; that specific check is done in application code — see
`result_matches_scores()` in
[`scripts/validate_examples.py`](../scripts/validate_examples.py), which
both example scripts and the test suite (`tests/test_schema_examples.py`)
run alongside the JSON Schema validation.

### Status

| Value | Meaning | Scores / result |
|---|---|---|
| `scheduled` | In the future, not yet played. | `null` / `null` |
| `completed` | Played to a normal finish. | Known integers (usual case), or both `null` with `result: "unknown"` if the score genuinely couldn't be confirmed. |
| `postponed` | Moved to a later date; *this* record has no outcome. | `null` / `null` |
| `cancelled` | Will not be played or rescheduled. | `null` / `null` |
| `abandoned` | Started but not finished (weather, crowd trouble, etc.). | No invented score; `result` is `null` or `void`. |

A postponed fixture that's later played is tracked as its own separate
record (own `event_id`, `status: completed`) — the postponed record is
not overwritten, since it documents the original scheduling and why it
didn't happen as planned. See `schema/examples/postponed_match.json` for
an example with a note pointing at the eventual replay date.

### Home/away on neutral venues

For fixtures at a neutral venue (cup finals, tournaments), `home_team` and
`away_team` follow the governing body's official match-sheet designation
(kit colours, listing order), not the actual location of the venue.

### Venue

`venue` is an optional object with optional `name`, `city`, and `country`
sub-fields. Include whichever is known; omit the whole object if nothing
about the venue is known.

### Verification status

| Value | Meaning |
|---|---|
| `unverified` | Taken from a single source, not yet cross-checked. |
| `verified` | Cross-checked against at least one independent additional source and consistent. |
| `conflicting` | Independent sources disagree, and this is unresolved. |
| `disputed` | The historical record itself is contested (e.g. among official bodies), independent of how well-sourced this pipeline's own research is. |

### Provenance

`source`, `source_url`, and `source_accessed_at` are required on every
record, including postponed/cancelled/abandoned ones — provenance is what
makes a "no result here" record trustworthy rather than indistinguishable
from a bug. All three travel with the record itself rather than being
tracked separately, so a record is self-contained and auditable on its
own.

## Extensibility to other sports

Kept deliberately generic for this reason:

- `sport` is a free `snake_case` string (not a fixed enum), so adding
  `basketball` or `tennis` doesn't require touching this schema file.
- `home_score`/`away_score` are named generically enough to cover
  goals, points, runs, etc. Sports that need more structure than a single
  final number per side (e.g. sets in tennis, innings in cricket) are out
  of scope for now — this schema only claims to cover a single final
  score per side, which is what the "at least" field list in the project
  brief asked for. Extending it for such sports is a future schema
  version, not a v1 concern.
- `result`'s `draw` value only applies to sports where draws exist; that's
  a documentation-level nuance the schema doesn't need to enforce, since a
  sport pipeline that never produces draws simply never emits that value.

## Suitability for CSV / JSON / Excel export

Every field except `venue` is a flat scalar (string, integer, or null),
which maps directly onto both JSON and tabular formats. `venue` is the one
nested object; when flattening for CSV/Excel later, the intended
convention is dotted column names — `venue.name`, `venue.city`,
`venue.country` — so no information is lost and the mapping back to JSON
is unambiguous. No exporter is implemented yet; this section only records
the intended convention for when one is.

## Validating records

```bash
cd sports-research-agent
pip install -r requirements.txt
python3 scripts/validate_examples.py
```

or as part of the regular test suite:

```bash
python3 -m unittest discover
```
