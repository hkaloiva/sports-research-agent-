# Limitations

Honest accounting of what this build does and doesn't do. Referenced
from `docs/architecture.md` and the final build report.

## Zero-cost requirement: fully met

No code path anywhere in `sports_research/` calls OpenAI, Anthropic, or
any paid search/scraping API. The only optional integrations
(Playwright, Ollama) are themselves free and local. Verified by reading
every network-touching module, not just asserted.

## Cannot be live-tested inside this development sandbox

Confirmed directly (not assumed): outbound HTTPS to arbitrary external
domains — including a neutral control, `example.com` — returns `403`
from this sandbox's egress proxy, for raw `curl`, the `WebFetch` tool,
and plain Python `requests` alike. This is a sandbox-level network
policy, established across Steps 6–8 of this project and reconfirmed
while building this standalone application. It is **not** a limitation
of the code — `tests/live/run_live_smoke_tests.sh` runs the exact same
CLI a real user would, and must be run on a machine with real internet
access. See `tests/live/README.md`.

## Request normalization is rule-based, not a general NLU system

`sports_research/research/normalizer.py` recognizes a small, documented
list of competitions and a handful of phrasing patterns (season
slash-form, explicit date ranges, "and"/"vs" participant coordination,
"men's/women's singles/doubles"). It correctly handles the build spec's
four example queries and several variations tested against it, but:

- An unrecognized competition/sport always produces
  `status: needs_clarification` rather than a wrong guess — safe, but
  means genuinely novel phrasing often needs clarification rather than
  "just working."
- Multi-word team names not in a coordination list (e.g. "Manchester
  United vs Everton" without "and"/"vs" as an exact separator) may not
  split correctly from surrounding text.
- No synonym/alias handling beyond the specific list in
  `_AMBIGUOUS_TEAM_ALIASES` and `_COMPETITIONS`.
- Sentence-initial capitalization vs. proper-noun capitalization is a
  known hard problem this regex-based approach only partially handles
  (mitigated with a stopword list, not solved in general).

## Extraction: two documented patterns, not general-purpose

See `docs/extraction.md § Known limitations` in full. In short:
inline two-participant score lines and ranked placement lists are
handled; arbitrary HTML table layouts, results-grid formats (like
Wikipedia's home-row/away-column season matrix), and prose-embedded
results outside these two shapes are not extracted by the deterministic
path. The optional local LLM assist is the documented extension point
for such pages — never required, but real page coverage without it is
necessarily partial.

## Placement events: one per page, approximate date when unspecified

`extract_placement_event()` builds one event from every ranked line on a
page — a season with multiple distinct contest stops needs a source that
separates them, or doesn't get properly segmented. When a request gives
only a season (no more specific date), `ResearchEngine` falls back to
`{season}-01-01` as a placeholder event date — a real approximation,
called out here rather than silently.

## Content retrieval

- Fetches a **single page** per candidate source — no pagination/crawl
  logic to follow "next page" links within a source's own archive.
  `MAX_SOURCES_TO_FETCH` controls how many different sources are tried,
  not how deep into one source's archive the application goes.
- `robots.txt` unreachable → fails open (treated as unrestricted) — a
  documented heuristic, not a certainty.
- `BrowserContentProvider` is an outright preference when enabled, not a
  smart "only when the plain HTTP fetch looks thin" fallback.
- No retry/backoff for transient HTTP failures — a timeout or 5xx is
  recorded as a failed source, not retried.

## Cross-source verification

- No fuzzy/approximate name matching for deduplication — a deliberate
  precision-over-recall choice (see `docs/validation.md`), but it does
  mean a genuine duplicate reported under two spelling variants of a
  team/competitor name won't be detected as the same event.
- `verification_status: "disputed"` exists in the schema but no code
  path currently sets it — no historically-contested-record detection is
  implemented.
- Only two sources are typically compared in practice (bounded by
  `MAX_SOURCES_TO_FETCH`, default 5, further narrowed by how many of
  those actually retrieve successfully and mention the same event) —
  "cross-source verification" here means "however many independent
  sources were actually found and fetched in this run," not an
  exhaustive search of the whole web.

## Completeness

`missing` is only ever a real number for competitions with a documented
structure rule — currently just Premier League seasons (inherited from
Step 5's planner). Every other request reports `expected: unknown`.

## Packaging for non-technical users

Currently requires: Python 3.11+, `pip install`, and running from a
cloned repository via `sports-research` (or `python -m sports_research.cli`).
To make this usable by someone who isn't comfortable with a terminal
would require, at minimum:

- A packaged executable (e.g. PyInstaller/`briefcase`) bundling Python
  and dependencies, so no `pip install` step is needed.
- The local web UI (`sports_research/webapp.py`) becoming the primary
  interface, auto-launched, rather than requiring `python -m
  sports_research.webapp` from a terminal.
- Bundled/documented Playwright browser installation if that path is
  meant to be available out of the box (currently opt-in and manual by
  design, to avoid an unwanted large download).
- Platform-specific installers (`.dmg`, `.exe`, or similar) and a
  signed/notarized build for macOS/Windows Gatekeeper/SmartScreen to not
  block it.

None of this is built in this session — explicitly out of scope for "a
developer can `git clone`, `pip install`, run" per the build spec, but
listed here since the final report asks what non-technical packaging
would require.

## Web UI

Deliberately minimal (per the build spec: "Do NOT spend time on visual
design") — functional only, no styling, no session persistence beyond
an in-memory dict keyed by a run ID (restarting the Flask process loses
prior runs' download links). Not intended as a production deployment
target (no auth, no multi-user isolation, `debug=False` but otherwise
unhardened) — a local convenience tool, matching its stated purpose.

## `teams`/`home_away` naming in ResearchRequest

Not renamed to `participants`/`role` for the sport-generic build — see
`docs/migration.md` for why this was a deliberate, documented choice
rather than an oversight.
