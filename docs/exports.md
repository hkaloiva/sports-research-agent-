# Exports

All three formats are written from the same `ResearchOutcome` (the
in-memory result of `ResearchEngine.run()`) — never re-derived from a
different code path, so they're always consistent with the report/CLI
output for the same run.

## CSV — `sports_research/export/csv_export.py`

One row per **(event, participant)** pair — the standard, lossless way to
flatten a one-to-many relationship into a flat table, and it works
uniformly whether an event has 2 participants (a football match) or N
(a placement-based leaderboard). Event-level columns (`event_id`,
`sport`, `competition`, `season`, `date`, `status`, `result`, `source`,
...) repeat on every row for that event; participant-level columns
(`participant_name`, `participant_role`, `participant_score`,
`participant_placement`) vary. Written via pandas (`DataFrame.to_csv`).

## JSON — `sports_research/export/json_export.py`

The full `ResearchOutcome`, structured: `request`, `plan`, `sources`,
`records`, `validation_problems`, `duplicate_groups`,
`verification_by_group`, `completeness`. The most complete export — CSV
and XLSX are projections of this same data for spreadsheet users.

## Excel (.xlsx) — `sports_research/export/xlsx_export.py`

Via `openpyxl`. Four sheets, as specified:

1. **Results** — same shape as the CSV export (one row per event/participant).
2. **Sources** — `source_id`, `title`, `url`, `domain`, `retrieved_at`,
   `retrieval_status`, `source_type` for every source consulted,
   including ones that failed to retrieve.
3. **Research Summary** — raw query, status, queries executed, sources
   found/retrieved, records extracted, completeness figures, duplicate
   count, and verified/conflicting/unverified counts.
4. **Validation Issues** — every schema/business-rule problem found,
   keyed by `event_id`.

## CLI usage

```bash
sports-research --output csv --output json --output xlsx --output-dir out "..."
```

`--output` is repeatable; default is `json` alone if omitted. Output
filenames are a slug of the query, e.g. `find_every_arsenal_....json`, in
`--output-dir` (default: `OUTPUT_DIR` from `.env`, `data/exports/`).
