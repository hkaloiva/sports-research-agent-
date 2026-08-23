"""Execute a SearchPlan's queries and return structured SearchResult objects.

This module never performs extraction, scraping, or browser automation —
it only turns raw search-provider hits into structured, deduplicated
results (see schema/search_result.schema.json). It is deliberately
backend-agnostic: `SearchBackend` is any callable `query -> list[dict]`.

Why a pluggable backend, and not an embedded HTTP client: this sandbox's
outbound HTTPS to search engines is blocked by organization egress policy
(confirmed with a direct test — 403 from the proxy for both a
key-less search API and a plain search-engine page), and even if it
weren't, parsing a search engine's HTML response would be scraping, which
this step explicitly excludes. The one reliable, key-less, non-scraping
web-search capability available in this environment is the orchestrating
agent's own WebSearch tool. That tool isn't importable from a standalone
Python process, so the boundary here is exactly at "raw search results as
data" — a backend that already has those results (e.g. captured from a
real WebSearch call, or a fixture in tests) plugs into the same code path
either way. See docs/search-module.md.
"""

from urllib.parse import urlsplit


class MalformedSearchHitError(ValueError):
    """Raised when a backend returns a hit missing a required field.

    Never silently skipped or filled in — a malformed hit is a backend
    defect, not something to guess around.
    """


def _domain_of(url: str) -> str:
    hostname = urlsplit(url).hostname
    if not hostname:
        raise MalformedSearchHitError(f"could not parse a domain from url: {url!r}")
    return hostname.lower()


def _validate_raw_hit(hit: dict, query: str) -> None:
    if not isinstance(hit, dict):
        raise MalformedSearchHitError(f"raw hit for query {query!r} is not an object: {hit!r}")
    title = hit.get("title")
    url = hit.get("url")
    if not isinstance(title, str) or not title:
        raise MalformedSearchHitError(f"raw hit for query {query!r} is missing a non-empty 'title': {hit!r}")
    if not isinstance(url, str) or not url:
        raise MalformedSearchHitError(f"raw hit for query {query!r} is missing a non-empty 'url': {hit!r}")


def build_search_execution(plan: dict, backend, provider: str, retrieved_at: str) -> dict:
    """Run every query in a SearchPlan through `backend` and return a
    SearchExecution dict: {research_request_id, provider, executed_at,
    queries_executed, results}. `results` is a flat, deduplicated list of
    SearchResult dicts (schema/search_result.schema.json).

    `backend(query: str) -> list[dict]` must return raw hits with at
    least 'title' and 'url'; 'snippet' is optional. Never fabricates a
    result: a hit missing title/url raises MalformedSearchHitError rather
    than being invented or silently dropped.

    Deduplication is on exact URL string equality only — no normalization
    (trailing slash, http vs https, etc.), since altering the provider's
    exact URL to decide "sameness" would itself be a kind of invention.
    When the same URL recurs for a different query, that query is added
    to the existing result's query_used list; the title/snippet already
    recorded are kept as first-seen (not overwritten), so provider text is
    never silently replaced.
    """
    queries_executed = [q["query"] for q in plan["search_queries"]]

    results_by_url = {}
    order = []

    for query in queries_executed:
        raw_hits = backend(query)
        for hit in raw_hits:
            _validate_raw_hit(hit, query)
            url = hit["url"]
            if url not in results_by_url:
                results_by_url[url] = {
                    "schema_version": "1.0.0",
                    "title": hit["title"],
                    "url": url,
                    "snippet": hit.get("snippet"),
                    "query_used": [query],
                    "domain": _domain_of(url),
                    "provider": provider,
                    "retrieved_at": retrieved_at,
                }
                order.append(url)
            else:
                existing = results_by_url[url]
                if query not in existing["query_used"]:
                    existing["query_used"].append(query)

    return {
        "schema_version": "1.0.0",
        "research_request_id": plan["research_request_id"],
        "provider": provider,
        "executed_at": retrieved_at,
        "queries_executed": queries_executed,
        "results": [results_by_url[url] for url in order],
    }


def mock_backend(fixture: dict):
    """Build a backend from an in-memory {query: [raw_hit, ...]} mapping.
    A query with no fixture entry returns an empty list (not an error —
    a real backend can legitimately find nothing for a given phrasing)."""

    def backend(query: str):
        return fixture.get(query, [])

    return backend


def prefetched_backend_from_file(path):
    """Build a backend from a JSON file of {query: [raw_hit, ...]}.

    Used for the live run: the file holds real WebSearch tool output,
    captured by the orchestrating agent (not fabricated, not scraped) and
    handed to this module through the same interface `mock_backend` uses
    in tests — no different code path for 'live' vs 'test'.
    """
    import json

    fixture = json.loads(path.read_text() if hasattr(path, "read_text") else open(path).read())
    return mock_backend(fixture)
