# Search Module — Executing a SearchPlan

This is the first step in this project that touches the real internet.
It executes a `SearchPlan`'s queries (see
[`search-strategy.md`](search-strategy.md)) and returns structured
`SearchResult` objects (see
[`schema/search_result.schema.json`](../schema/search_result.schema.json)).
It does **not** extract sports results and does **not** export CSV/Excel
— those come later.

## Why the backend is pluggable, not embedded

Two things were checked directly before writing any code:

1. **Raw outbound HTTPS from this sandbox to a search engine is blocked
   by organization egress policy.** A key-less JSON search API and a
   plain search-engine page both returned `403` from the proxy — the
   proxy's own guidance is explicit: don't retry or route around a policy
   denial, report it. So a Python `requests`-based search client isn't an
   option here, independent of scraping concerns.
2. **The `WebSearch` tool (available to the orchestrating Claude Code
   agent) works** — confirmed with a real call, which returned real
   Wikipedia/Arsenal.com/FBref/PremierLeague.com results. That tool isn't
   importable from a standalone Python process, though — it's called
   through the agent's own tool-call protocol, not a library.

So the "simplest reliable web-search capability available in this
environment" is real, but it lives one layer up from the Python module,
not inside it. [`search.py`](../search.py) reflects that honestly: it
takes a `backend` — any callable `query -> list[raw_hit]` — instead of
hard-coding an HTTP client or, worse, parsing a search engine's HTML
(which would be scraping, explicitly out of scope for this step). Tests
use `mock_backend()` with an in-memory fixture. The live run uses
`prefetched_backend_from_file()`, pointed at a JSON file holding real
`WebSearch` output that the orchestrating agent captured directly — the
exact same `build_search_execution()` code path runs either way; only
where the raw hits come from differs. Nothing about a live run is
special-cased or exempt from the schema/validation the tests exercise.

## What the module guarantees

- **Never fabricates.** A raw hit missing `title` or `url` raises
  `MalformedSearchHitError` — it is never invented, defaulted, or
  silently dropped. A `snippet` a backend didn't supply is `null`, never
  synthesized from other text.
- **Preserves the exact URL and title** the backend returned — no
  normalization, canonicalization, or rewriting.
- **Preserves which query produced each result** via `query_used`; when
  the same URL is returned by more than one query, that list grows
  rather than the result being duplicated.
- **Deduplicates on exact URL string equality only.** No normalization
  (trailing slash, `http` vs `https`, etc.) is applied before comparing —
  altering the provider's URL to decide "sameness" would itself be a
  kind of invention.
- **Keeps different domains — and different URLs on the same domain —
  as separate results.** `domain` is a derived, informational field used
  for nothing else; it never triggers merging.

## Running it

```bash
cd sports-research-agent
python3 scripts/search_cli.py <research_request.json> --backend-fixture <raw_hits.json> [--provider NAME] [--out out.json]
```

`<raw_hits.json>` is `{query: [{"title": ..., "url": ..., "snippet": ...}, ...]}`.

## Tests

```bash
python3 -m unittest discover
```

`tests/test_search.py` covers deduplication (including the "not the same
URL" and "same domain, different URLs" cases), provenance preservation,
the never-fabricate guarantees, and schema validation of generated
results — all with mocked backends, no live internet.
