# Research Request — Data Model

This document explains `ResearchRequest`: a structured representation of
what a user is asking the research system to find. It is **not** result
data (see [`docs/data-schema.md`](data-schema.md) /
[`schema/result_record.schema.json`](../schema/result_record.schema.json)
for that) and it does **not** run any research — no web search, scraping,
or agent logic exists yet. This is only the request shape that a future
research step would eventually consume.

The machine-readable schema is
[`schema/research_request.schema.json`](../schema/research_request.schema.json)
(JSON Schema, draft 2020-12). Five example requests, one per required
category, live in
[`schema/examples/research_requests/`](../schema/examples/research_requests/).

## The core problem: explicit vs. inferred

A request like *"Find all Arsenal Premier League results from 2003/04"*
mixes two very different kinds of information:

- **What the user actually said**: Arsenal, Premier League, the season
  "2003/04".
- **What a system could plausibly fill in**: that this is a football
  request (the user never said "football"), a default output format, a
  default verification requirement — and, dangerously, a temptation to
  turn "2003/04" into concrete match dates.

That last temptation is exactly what this model exists to prevent. There
is no documented competition-calendar rule in this project mapping a
season string to actual fixture dates, so `date_from`/`date_to` must
**never** be invented from a season — a `ResearchRequest` for that query
carries `season` and nothing under `date_from`/`date_to` at all. See
[`schema/examples/research_requests/01_team_season.json`](../schema/examples/research_requests/01_team_season.json).

To make this distinction visible and machine-checkable rather than a
convention nobody enforces, every constraint in a `ResearchRequest` is
wrapped in a small envelope instead of being a bare value:

```json
{ "value": "football", "source": "inferred", "basis": "..." }
```

- **`source: "explicit"`** — the user stated this, verbatim or losslessly
  reformatted (see [Normalization is not inference](#normalization-is-not-inference)
  below). Never carries a `basis` — there's nothing to justify.
- **`source: "inferred"`** — the system filled this in. **Always** carries
  a `basis`: the specific documented rule used (see
  [Defaults](#defaults) below). The schema enforces this pairing — an
  `inferred` entry without a `basis`, or an `explicit` entry with one, is
  rejected.

A constraint the system has no documented way to resolve is not put in
`constraints` with a guessed value — it is left out entirely, and the
missing piece is surfaced in `clarifications_needed` instead (see
[Ambiguous requests](#ambiguous-requests) below). Absent from
`constraints` means "no constraint on this dimension" (e.g. no season
given → all seasons), which is different from "this is blocking and
unresolved" (→ `clarifications_needed`).

## Normalization is not inference

Reformatting what the user literally said, losslessly, is **not**
invention — no new constraint is being added, only its representation is
being standardized. `"2003/04"` and `"2003-2004"` denote the same season;
storing the canonical form in `value` while preserving the original in
`raw_value` keeps `source: "explicit"`:

```json
"season": { "value": "2003-2004", "source": "explicit", "raw_value": "2003/04" }
```

`raw_value` is optional and only present when a reformat happened.
Compare this with genuine inference below, where the system is adding
information the user didn't provide at all.

## Defaults

Every `inferred` entry's `basis` must point at one of these documented
rules. If a request needs a value this list doesn't cover, it must go to
`clarifications_needed` — the rule list is the whole point: it's what
keeps "inferred" from silently meaning "guessed".

1. **Sport entailed by competition.** If the competition named is one
   this project only knows as football (currently: all of them — Premier
   League, UEFA Champions League, FIFA World Cup, La Liga, FA Cup, Copa
   América, UEFA European Championship, European Cup), `sport` may be
   inferred as `"football"`, citing the specific competition as the
   reason it's unambiguous.
2. **Sport defaults to football when nothing suggests otherwise.** If no
   competition is named either, `sport` may still be inferred as
   `"football"`, citing that the project currently only supports
   football (see the top-level `README.md`) — but only when nothing in
   `raw_query` implies a different, unsupported sport. If it does, that's
   a clarification, not a default.
3. **`required_fields` defaults to the core outcome fields** — `date`,
   `home_team`, `away_team`, `home_score`, `away_score`, `result` — when
   the user didn't specify which fields they need back.
4. **`verification` defaults to `"required"`** when unspecified — a
   conservative default that favors not returning unverified data over
   convenience.
5. **`output_format` defaults to `"json"`** when unspecified.

There is deliberately **no** rule mapping `season` to `date_from`/
`date_to` — that would require a real competition calendar/fixture-list
source this project doesn't have. Don't add one to this list without
building that source first.

## Ambiguous requests

`status` is `"ready"` or `"needs_clarification"`. When something the
request depends on is missing or genuinely ambiguous — not just
"unspecified, so no constraint on that dimension", but "blocking, and
guessing would silently narrow or misdirect the request" — the request
carries `status: "needs_clarification"` and one entry per open question
in `clarifications_needed`:

```json
{
  "field": "teams",
  "question": "Which club named 'United' do you mean — e.g. Manchester United, Newcastle United, West Ham United, or Leeds United?",
  "reason": "'United' matches multiple well-known football clubs and the request does not disambiguate which one."
}
```

The schema enforces consistency both ways: `status: "ready"` requires
`clarifications_needed` to be empty (a request can't claim to be ready
while something's still open), and `status: "needs_clarification"`
requires at least one entry (a request can't claim ambiguity without
saying what's ambiguous). See
[`schema/examples/research_requests/05_ambiguous_needs_clarification.json`](../schema/examples/research_requests/05_ambiguous_needs_clarification.json) —
note that fields unrelated to the ambiguity (like `sport`,
`required_fields`) are still safely defaulted; clarification is targeted
at the specific unresolved fields, not a blanket refusal.

## Field reference

| Field (under `constraints`) | Value type | Meaning |
|---|---|---|
| `sport` | string, `snake_case` | Same vocabulary as `result_record.schema.json`'s `sport`. |
| `competition` | string | Competition/league/tournament name. |
| `season` | string, `YYYY` or `YYYY-YYYY` | Canonical season, same format as the result schema. |
| `date_from` / `date_to` | ISO 8601 date or date-time | Inclusive event-date bounds. Never inferred from `season` (see [Defaults](#defaults)). |
| `teams` | array of strings, ≥1 | One or more team names. Two entries conventionally means head-to-head (matches where both appear, either order) — a documentation convention, not a separate structural field. |
| `venue` | object `{name?, city?, country?}` | Same shape as the result schema's `venue`. |
| `home_away` | `home`/`away`/`any` | Relative to the first entry in `teams`. Meaningless without `teams` — documented, not schema-enforced. |
| `result_types` | array of `home_win`/`away_win`/`draw`/`void`/`unknown` | Restrict to these outcomes. |
| `required_fields` | array, values restricted to `result_record.schema.json`'s own field names | Which fields the eventual response must include. |
| `output_format` | `json`/`csv`/`excel` | Requested export format. |
| `verification` | `required`/`not_required` | Whether returned records must already be `verification_status: verified`. |

Top-level fields: `raw_query` (the literal request text), `status`,
`constraints` (the object above), `clarifications_needed` (array,
possibly empty), and optional `schema_version`.

## The 5 required examples

| File | Category |
|---|---|
| `01_team_season.json` | All matches for a team in a season |
| `02_head_to_head.json` | Head-to-head matches between two teams |
| `03_competition_date_range.json` | All matches in a competition over a date range |
| `04_result_type_filter.json` | Matches matching a particular result type |
| `05_ambiguous_needs_clarification.json` | Intentionally ambiguous — needs clarification |

## Validating requests

```bash
cd sports-research-agent
python3 scripts/validate_research_requests.py
```

or as part of the full suite:

```bash
python3 -m unittest discover
```

Unlike `result_record.schema.json`, no extra Python-level business rule
was needed here — every cross-field rule in this schema (`status` vs.
`clarifications_needed`, `source` vs. `basis`) is a plain value/enum
comparison, fully expressible in JSON Schema's `if`/`then` on its own.
`validation.py`'s `validate_request()` is schema-only for this reason.
