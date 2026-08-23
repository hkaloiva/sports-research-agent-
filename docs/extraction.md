# Extraction

**Updated for the standalone application.** Step 7's original content
about the top-level `extractor.py` module (a football-only,
pipe-delimited-line parser built when `WebFetch` was found to be blocked
in the Claude Code sandbox) is preserved below under
[Step 7's extractor.py (still present, superseded)](#step-7s-extractorpy-still-present-superseded)
— that module still exists, unchanged, for backward compatibility, but
`sports_research/extraction/` is what the standalone application actually
uses now that real page content is available via `ContentProvider`
(`docs/retrieval.md`).

## FREE/LOCAL: DeterministicExtractor

`sports_research/extraction/deterministic.py`. Two tractable, documented
patterns operating on real page text (not agent-summarized text):

1. **`extract_two_participant_events()`** — scans for `"Name1 X-Y Name2"`
   score lines, carrying forward the most recently seen date line. Works
   for any two-participant sport with a numeric score each side, not just
   football (the pattern has no football-specific assumption). A score
   line seen before any date, or with an unparseable name/score, is
   reported in `ExtractionResult.ambiguous` — never guessed.
2. **`extract_placement_event()`** — scans for ranked-list lines
   (`"1. Name"`, `"2) Name"`, `"1st Name"`) and builds **one** event whose
   participants carry each competitor's `placement` (and `score`, if a
   trailing number was present). Used for individual/motorsport events
   where the result is a ranking, not a two-side score. The event's
   `date` must be supplied by the caller — a leaderboard page rarely
   repeats the event date on every row, so this function never invents
   one.

Neither pattern is a general solution to "extract facts from arbitrary
web text" — see [Known limitations](#known-limitations).

## OPTIONAL: local LLM assist

`sports_research/extraction/local_llm.py` +
`sports_research/extraction/engine.py`'s `ExtractionEngine`. Disabled by
default (`OLLAMA_ENABLED=false`). When enabled:

- `ollama_available()` checks whether a local Ollama server
  (https://ollama.com — free, runs entirely on the user's machine, no
  cloud API) is actually reachable *right now*. Never raises.
- Only called when `DeterministicExtractor` found **zero** records for a
  page — `ExtractionEngine.extract_two_participant()` never probes Ollama
  when deterministic extraction already succeeded.
- If Ollama isn't reachable, extraction silently (but reportedly, via
  `ExtractionOutcome.capability_note`) falls back to "no records from
  this page" — the application never crashes for lacking this optional
  capability.
- The model's job is deliberately narrow: reformat page text into the
  same `"DATE:" + "Name X-Y Name"` lines `extract_two_participant_events()`
  already parses, so its output goes through the same tested parser —
  no new, unvalidated LLM-output parser to trust.
- No model is ever downloaded automatically. The user must have already
  run `ollama pull <model>` themselves.

## Extraction is separate from validation

`ExtractionEngine`/`deterministic.py` never import
`sports_research/validation/` — the same separation Step 7 established,
now enforced across the whole extraction subsystem, not just one module.
Validation (`docs/validation.md`) happens as an explicit, later stage in
`ResearchEngine.run()`.

## Data normalization

`sports_research/extraction/normalize.py`: `normalize_date()` (ISO,
`DD/MM/YYYY`, `"16 August 2003"`, `"August 16, 2003"` — returns `None`
rather than guessing on anything else), `normalize_name()` (whitespace
collapse, footnote-marker stripping — never changes substantive spelling),
`normalize_score()` (integer-only; a decimal or non-numeric token returns
`None` rather than rounding/truncating).

## Known limitations

- **Pattern-based extraction from arbitrary web text is a genuinely hard,
  unsolved-in-general problem.** These two patterns cover common,
  tractable cases (an inline score line, a ranked list) — they do not
  handle every real page's layout (e.g. an HTML `<table>` whose text
  extraction interleaves columns in an order these line-based regexes
  don't expect, or a results grid like Wikipedia's home-row/away-column
  season matrix). This is the documented extension point for the optional
  local LLM assist, not a claim of general-purpose extraction.
- **The score-line regex can false-positive on non-match text that
  happens to contain a number pattern** (e.g. a page heading like
  "Premier League 2003-04 results" can be mis-parsed as a candidate score
  line). The safe failure mode holds: such lines are reported as
  `ambiguous`, never turned into a fabricated record — but this does add
  some noise to `ambiguous` output on real pages.
- **`extract_placement_event()` currently produces one event per fetched
  page**, using every ranked line found on it. A season with multiple
  distinct events/stops (e.g. multiple 2015 Street League Skateboarding
  contest stops across the year, not one single final) needs a source
  page that separates them, or a future revision that segments a page
  into multiple placement events — not implemented in this build.
- **`extract_placement_event()`'s `date` isn't always available** from a
  `ResearchRequest` that only specifies a season — `ResearchEngine`
  currently falls back to `{season}-01-01` in that case
  (`sports_research/research/engine.py`), which is a real approximation,
  not the actual event date, and is called out explicitly here rather
  than silently.

---

## Step 7's extractor.py (still present, superseded)

The remainder of this document is Step 7's original content, describing
the top-level `extractor.py` module built when this project ran inside a
Claude Code session and found `WebFetch` blocked. That module still
exists unchanged (`extractor.py`, `scripts/extract_cli.py`,
`tests/test_extractor.py`) — nothing here was deleted — but it is
football-only (participant field names `home_team`/`away_team`) and
worked from a pipe-delimited proxy text format rather than real fetched
page content. The standalone application's `ResearchEngine` uses
`sports_research/extraction/` (above), not this module.

This is `docs/extraction.md`: converting raw source content into
canonical `result_record` entries (see [`data-schema.md`](data-schema.md)).
It also records why **no live extraction run was performed** for Step 7 —
that was a real finding about the Claude Code sandbox's capabilities at
the time, not an oversight. See git history for that original document's
full text if needed; the essential facts (input format, the
extraction/validation separation, the never-invented fields, the
honesty-about-completeness principle) all carry forward unchanged into
the new system described above.
