# Sports Research Agent

A standalone local application: enter a natural-language historical
sports research request, and it searches the internet, retrieves real
source pages, extracts structured results, cross-checks them across
sources, and exports CSV/JSON/Excel.

```bash
sports-research "Find every Arsenal Premier League result from the 2003/04 season."
sports-research "Find the results of the 2015 Street League Skateboarding competitions."
```

**Zero mandatory cost.** No Claude Code, no Claude Chat, no OpenAI/Anthropic
API, no paid search or scraping subscription. The default configuration
uses only free, key-less services (DuckDuckGo search via `ddgs`, plain
HTTP retrieval, Wikipedia's own search API). Optional local-only
extras (Playwright browser rendering, an Ollama local LLM assist) are
genuinely optional — the application works fully without them. See
`docs/limitations.md` for exactly what this does and doesn't guarantee.

## Quick start

**Linux/macOS** — one command, creates a virtual environment, installs
everything, and runs the test suite to confirm it worked:

```bash
git clone https://github.com/hkaloiva/sports-research-agent-.git
cd sports-research-agent-
./setup.sh
source .venv/bin/activate
sports-research "Find every Arsenal Premier League result from the 2003/04 season."
```

**Windows, no Python/git needed** — download the packaged `.exe` from the
latest [Release](https://github.com/hkaloiva/sports-research-agent-/releases),
unzip, and run `sports-research.exe` — see `docs/windows-executable.md`.

**Windows, from source** (PowerShell or cmd — no bash needed):

```powershell
git clone https://github.com/hkaloiva/sports-research-agent-.git
cd sports-research-agent-
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m unittest discover
sports-research "Find every Arsenal Premier League result from the 2003/04 season."
```

**Manual install, any platform** (what `setup.sh` does, step by step):

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: python -m venv .venv && .venv\Scripts\activate
pip install -e .          # installs dependencies AND registers the `sports-research` command
python3 -m unittest discover   # optional — confirms the install works, no internet required
sports-research "..."
```

`pip install -r requirements.txt` alone installs only the third-party
dependencies — it does **not** register the `sports-research` command
(that comes from installing this project's own package via
`pip install -e .`, which also installs every dependency
`requirements.txt` lists, since `pyproject.toml` declares the same set).
If you only ran `pip install -r requirements.txt`, use
`python3 -m sports_research.cli "..."` instead of the bare
`sports-research` command.

Interactive mode: run `sports-research` with no argument. Exports:
`--output csv --output json --output xlsx --output-dir out`. Local web
UI: `python3 -m sports_research.webapp`, then open
`http://localhost:5000`.

## Sport-generic by design

Not football-specific: the canonical `EventResult` model
(`schema/event_result.schema.json`) generalizes "two teams with scores"
into N participants, each with an optional score and/or placement — the
same shape covers football, tennis, skateboarding, motorsport, and
anything else. Proven with a full-pipeline test on a non-football
(skateboarding) request, not just asserted — see
`tests/sports_research/research/test_engine.py::TestResearchEngineNonFootballSport`.

## Architecture

```
Request -> normalize -> plan -> search -> rank -> retrieve -> extract
  -> normalize -> validate -> dedup -> cross-source compare
  -> completeness check -> report -> CSV/JSON/XLSX
```

Every stage is an independently testable module under
`sports_research/`. Full diagram and module map: `docs/architecture.md`.
Every other stage's design decisions have their own doc — see the table
below.

## How this project got here

This standalone application is the result of an 8-step build process
that started inside a Claude Code session (schema design, a
`ResearchRequest`/`SearchPlan` model, a search module using Claude
Code's own tools, extraction, and a web-access-options investigation —
all preserved, documented in `docs/data-schema.md` through
`docs/web-access-options.md`) before this final build replaced the
Claude-Code-tool dependency with real, standalone `SearchProvider`/
`ContentProvider` implementations. See `docs/architecture.md § Reused vs.
new` for exactly what carried over unchanged vs. what's new, and
`docs/migration.md` for the two schema changes involved.

## Project layout

```
sports-research-agent/
├── sports_research/            # the standalone application
│   ├── cli.py                    # sports-research entry point
│   ├── webapp.py                  # minimal local Flask UI
│   ├── config.py                   # zero-cost-by-default configuration (.env-driven)
│   ├── models/                      # EventResult, Source, result_record migration
│   ├── search/                       # SearchProvider: DuckDuckGo (default), Wikipedia (fallback)
│   ├── retrieval/                     # ContentProvider: HTTP (default), Playwright (optional)
│   ├── extraction/                     # DeterministicExtractor + optional local LLM (Ollama) assist
│   ├── validation/                      # schema validation, dedup, cross-source conflicts, completeness
│   ├── research/                         # NL normalizer, planner, source ranking, ResearchEngine
│   ├── export/                            # CSV, JSON, XLSX
│   ├── reporting/                          # human-readable research report
│   └── cache/                               # local file-based cache
├── config.py, validation.py, planner.py,   # Steps 1-8's original modules — unchanged, still
│   search.py, extractor.py                  # used by sports_research/ where reused (see docs/architecture.md)
├── schema/                     # every JSON Schema (result_record, event_result, research_request, ...)
├── data/{raw,processed,exports,cache}/
├── docs/                       # see table below
├── scripts/                    # Steps 1-8's standalone CLI tools (still present, unchanged)
├── tests/sports_research/      # the new application's test suite (mocked, no live internet)
├── tests/live/                 # network-required smoke tests — run on your own machine
├── tests/*.py                  # Steps 1-8's original tests — unchanged, still passing
├── requirements.txt, pyproject.toml, .env.example
```

## Documentation

| Doc | Covers |
|---|---|
| `docs/architecture.md` | Full pipeline, module map, what's reused vs. new |
| `docs/research-workflow.md` | What each pipeline stage does |
| `docs/data-model.md` | `EventResult`, `Source`, and the sport-generic design |
| `docs/migration.md` | The `result_record` → `EventResult` migration, the `ResearchRequest` extension |
| `docs/search.md` | `SearchProvider`s, source ranking |
| `docs/retrieval.md` | `ContentProvider`s, `robots.txt` compliance |
| `docs/extraction.md` | Deterministic patterns, optional local LLM assist |
| `docs/validation.md` | Schema/business rules, dedup, cross-source verification, completeness |
| `docs/exports.md` | CSV/JSON/XLSX format details |
| `docs/configuration.md` | Every `.env` setting, FREE/LOCAL vs. OPTIONAL |
| `docs/testing.md` | Test suite structure, live smoke tests |
| `docs/limitations.md` | Honest accounting of what isn't (fully) solved |

Plus the original Steps 1–8 docs (`docs/data-schema.md` through
`docs/web-access-options.md`), still accurate for the modules they
describe.

## Tests

```bash
python3 -m unittest discover
```

205 tests, all mocked, zero live internet required.

## Live acceptance tests (real internet, real sources — run on your own machine)

One command runs both of this project's acceptance-test queries against
the real, live `sports-research` CLI — real search providers (DuckDuckGo,
Wikipedia), real HTTP retrieval, no mocks:

```bash
bash tests/live/run_live_smoke_tests.sh
```

This is exactly `sports-research "Find every Arsenal Premier League
result from the 2003/04 season."` followed by `sports-research "Find the
results of the 2015 Street League Skateboarding competitions."` (the
second proves the pipeline isn't secretly football-specific), each with
`--output csv --output json --output xlsx`. Logs and exports land in
`tests/live/output/`. If internet access fails, the report honestly shows
zero sources/records found — it never fabricates a result. See
`tests/live/README.md` for why this can't run inside a Claude Code
sandbox and must be run on a real, internet-connected machine.
