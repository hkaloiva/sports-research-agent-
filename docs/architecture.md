# Architecture

Sports Research Agent is a standalone Python application. It runs
entirely on the user's own machine, using their own internet connection,
with **zero mandatory paid dependency** — no Claude Code, no Claude Chat,
no OpenAI/Anthropic API, no paid search or scraping API. See
`docs/limitations.md` for exactly what "standalone" does and doesn't mean
in practice, and `docs/configuration.md` for what's free-by-default vs.
optional.

## Pipeline

```
USER REQUEST
    │
    ▼
REQUEST NORMALISATION   sports_research/research/normalizer.py
    │                   (rule-based NL -> ResearchRequest, no LLM required)
    ▼
RESEARCH PLAN           sports_research/research/planner.py
    │                   (re-exports the existing planner.py — Step 5)
    ▼
SEARCH                  sports_research/search/  (SearchProvider)
    │
    ▼
SOURCE RANKING          sports_research/research/ranking.py
    │
    ▼
CONTENT RETRIEVAL       sports_research/retrieval/  (ContentProvider)
    │
    ▼
CONTENT EXTRACTION      sports_research/extraction/  (ExtractionEngine)
    │
    ▼
DATA NORMALISATION      sports_research/extraction/normalize.py
    │
    ▼
VALIDATION              sports_research/validation/schema_validation.py
    │
    ▼
DEDUPLICATION           sports_research/validation/dedup.py
    │
    ▼
CROSS-SOURCE COMPARISON sports_research/validation/conflicts.py
    │
    ▼
COMPLETENESS CHECK      sports_research/validation/completeness.py
    │
    ▼
RESEARCH REPORT         sports_research/reporting/report.py
    │
    ▼
CSV / JSON / XLSX       sports_research/export/
```

`sports_research/research/engine.py`'s `ResearchEngine.run()` is the only
place that orchestrates these stages together — every stage is a plain,
independently importable, independently testable function/module, and
`ResearchEngine` calls each one in turn rather than embedding pipeline
logic itself. See `docs/research-workflow.md` for what each stage
actually does and `docs/testing.md` for how each is tested in isolation.

## Reused vs. new

Steps 1–8 of this project (documented in `docs/data-schema.md`,
`docs/research-request.md`, `docs/search-strategy.md`,
`docs/search-module.md`, the original `docs/extraction.md`, and
`docs/web-access-options.md`) already built a football-only prototype of
most of this pipeline, running inside a Claude Code session using its
`WebSearch`/`WebFetch` tools. This standalone build:

- **Reuses unchanged**: `validation.py`, `planner.py`,
  `research_request.schema.json` (extended, not replaced — see
  `docs/migration.md`), `search_plan.schema.json`, `search.py`'s
  dedup-by-URL logic (`sports_research/search/base.py`'s
  `SearchProvider.search()` returns exactly the shape
  `search.build_search_execution()` already expects).
- **Generalizes**: `result_record.schema.json` (football-only) →
  `event_result.schema.json` (sport-generic) — see `docs/data-model.md`
  and `docs/migration.md`.
- **Replaces the Claude Code tool dependency with real, standalone code**:
  `sports_research/search/` (real `SearchProvider`s — DuckDuckGo,
  Wikipedia) and `sports_research/retrieval/` (real `ContentProvider`s —
  plain HTTP, optional local browser rendering) instead of `WebSearch`/
  `WebFetch`.
- **Adds what didn't exist yet**: extraction from real (not
  agent-fetched) page text, cross-source verification, deduplication,
  completeness checking, a research report, CSV/JSON/XLSX export, a CLI,
  and a minimal local web UI.

## Module map

```
sports_research/
    cli.py            CLI entry point (sports-research)
    webapp.py          Minimal local Flask UI
    config.py           Zero-cost-by-default configuration (.env-driven)
    models/
        event_result.py    EventResult builder (the sport-generic canonical record)
        source.py            Source record builder
        migration.py          result_record.schema.json -> event_result.schema.json
    search/
        base.py             SearchProvider interface, FallbackSearchProvider
        duckduckgo_provider.py   Zero-cost default (ddgs, no API key)
        wikipedia_provider.py    Zero-cost fallback (official Wikipedia search API)
    retrieval/
        base.py             ContentProvider interface
        http_provider.py     Plain HTTP + BeautifulSoup (respects robots.txt)
        browser_provider.py   Optional local Playwright rendering
    extraction/
        engine.py            ExtractionEngine: deterministic + optional local LLM
        deterministic.py      Pattern-based extraction (two-participant scores, placement lists)
        local_llm.py           Optional Ollama-backed assist (never required)
        normalize.py            Date/name/score normalization
    validation/
        schema_validation.py  JSON Schema + the one business rule per model
        dedup.py                Event-level duplicate detection
        conflicts.py              Cross-source verification classification
        completeness.py            Expected-vs-found reporting
    research/
        normalizer.py         Natural language -> ResearchRequest
        planner.py              Re-exports the existing ResearchRequest -> SearchPlan (Step 5)
        ranking.py                 Source prioritization
        engine.py                    ResearchEngine: orchestrates every stage
        factory.py                    Builds a ResearchEngine from Config
    export/
        csv_export.py, json_export.py, xlsx_export.py
    reporting/
        report.py             Human-readable research report
    cache/
        store.py              Local file-based cache + cached provider wrappers
```

Plus, at the repository root (unchanged from Steps 1–8):
`config.py`, `validation.py`, `planner.py`, `search.py`, `extractor.py`,
and `schema/*.schema.json`.
