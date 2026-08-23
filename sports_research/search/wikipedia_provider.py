"""Fallback SearchProvider: Wikipedia's own, official, documented,
key-less search API (action=query&list=search on the MediaWiki API).
Narrower than a general web search (wikipedia.org only) but zero-cost,
well-documented, and — per docs/web-access-options.md's research —
explicitly permits this kind of use provided a real User-Agent and
reasonable request volume (Wikimedia API Usage Guidelines).
"""

from .base import SearchProvider, SearchProviderError

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "SportsResearchAgent/0.1 (local research tool; contact: local-user@example.invalid)"


class WikipediaSearchProvider(SearchProvider):
    name = "wikipedia"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def search(self, query: str, max_results: int = 10) -> list:
        try:
            import requests
        except ImportError as e:
            raise SearchProviderError(f"the 'requests' package is not installed: {e}") from e

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max_results,
            "format": "json",
        }
        try:
            response = requests.get(
                WIKIPEDIA_API_URL, params=params, timeout=self.timeout,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as e:
            raise SearchProviderError(f"Wikipedia search failed for {query!r}: {e}") from e
        except ValueError as e:  # invalid JSON
            raise SearchProviderError(f"Wikipedia search returned invalid JSON for {query!r}: {e}") from e

        hits = []
        for item in payload.get("query", {}).get("search", []):
            title = item.get("title")
            if not title:
                continue
            url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            snippet = item.get("snippet")  # MediaWiki HTML-highlighted snippet, e.g. with <span class="searchmatch">
            hits.append({"title": title, "url": url, "snippet": snippet or None})
        return hits
