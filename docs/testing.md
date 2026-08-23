# Testing

```bash
cd sports-research-agent
python3 -m unittest discover
```

**205 tests, all passing, zero live internet access required.** Every
network-touching library (`ddgs`, `requests`, `playwright`) is mocked at
its call boundary — `unittest.mock.patch` on `ddgs.DDGS`, `requests.get`,
etc. — never a real network call.

## Coverage by area

| Area | File(s) | What's covered |
|---|---|---|
| Request parsing/ambiguity | `tests/sports_research/research/test_normalizer.py` | All 4 build-spec example queries + head-to-head splitting + ambiguous-alias clarification |
| Search planning | `tests/test_search_plan.py` (Step 5, reused) | Query generation, including the new `competition+season` branch |
| Search providers | `tests/sports_research/search/` | Fallback chain, DuckDuckGo (mocked `ddgs`), Wikipedia (mocked `requests`), never-fabricate on malformed hits |
| URL deduplication | `tests/test_search.py` (Step 6, reused) | Exact-URL dedup, `query_used` tracking |
| Content retrieval | `tests/sports_research/retrieval/` | Successful fetch (all required fields captured), HTTP errors, network errors, `robots.txt` compliance, unsupported content-type, Playwright unavailability |
| Extraction | `tests/sports_research/extraction/` | Two-participant + placement patterns, date/name/score normalization, local-LLM graceful degradation (both "Ollama unreachable" and "Ollama available, used only as fallback") |
| Validation/business rules | `tests/sports_research/validation/test_schema_validation.py` | Valid/invalid `EventResult`s, the score-comparison business rule |
| Cross-source conflicts | `tests/sports_research/validation/test_conflicts.py` | Agreement across independent domains → verified; same-domain → not independent; disagreement → conflicting, both claims preserved |
| Missing data / completeness | `tests/sports_research/validation/test_completeness.py` | Known vs. unknown expected count |
| Provenance | `tests/sports_research/models/test_event_result.py`, `test_migration.py` | Source/provenance fields threaded through correctly, migration from the Step 2 schema |
| CSV/JSON/XLSX export | `tests/sports_research/export/` | Row shape (incl. N-participant events), full-outcome round-trip, all 4 required XLSX sheets |
| CLI | `tests/sports_research/cli/test_cli.py` | `--help`, ambiguous-request path (exit code, clarification text, stage progress) |
| Web UI | `tests/sports_research/test_webapp.py` | Index page, ambiguous-request rendering, empty-query handling, unknown-download-id 404 |
| HTTP/malformed-page/search-provider failures | `tests/sports_research/research/test_engine.py` | Full-pipeline integration: search failure, content-retrieval failure, malformed extraction inputs — all handled without crashing |
| **Not football-specific** | `tests/sports_research/research/test_engine.py::TestResearchEngineNonFootballSport` | Full pipeline run on a skateboarding request, placement-based extraction, valid `EventResult` output |

Plus everything from Steps 1–8 (92 tests: schema examples, the 20-record
test dataset, `ResearchRequest`/`SearchPlan`/`SearchResult` validation) —
unchanged, still passing.

## Live smoke tests — separate, network-required, run on your own machine

`tests/live/` — **not** part of `python3 -m unittest discover` (nothing
there matches the `test_*.py` discovery pattern). See
`tests/live/README.md` for why they can't run inside this development
sandbox and exactly how to run them yourself:

```bash
bash tests/live/run_live_smoke_tests.sh
```
