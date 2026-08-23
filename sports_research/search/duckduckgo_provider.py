"""Zero-cost default SearchProvider: DuckDuckGo, via the `ddgs` package.

No API key, no paid account. `ddgs` wraps DuckDuckGo's public HTML/lite
search endpoints (no automated-query API is offered by DuckDuckGo, but
none is needed — no login, no CAPTCHA-gated flow, no bypassing of any
access control). This provider cannot be exercised in this sandbox
(WebFetch/raw HTTP are blocked here — see docs/limitations.md) but is
tested with a mocked `ddgs.DDGS` below; a real network run must happen
on the user's own machine (see tests/live/).
"""

from .base import SearchProvider, SearchProviderError


class DuckDuckGoSearchProvider(SearchProvider):
    name = "duckduckgo"

    def search(self, query: str, max_results: int = 10) -> list:
        try:
            from ddgs import DDGS
            from ddgs.exceptions import DDGSException
        except ImportError as e:
            raise SearchProviderError(f"the 'ddgs' package is not installed: {e}") from e

        try:
            with DDGS() as client:
                raw_results = client.text(query, max_results=max_results)
        except DDGSException as e:
            raise SearchProviderError(f"DuckDuckGo search failed for {query!r}: {e}") from e
        except Exception as e:  # network/library errors not covered by DDGSException
            raise SearchProviderError(f"DuckDuckGo search failed for {query!r}: {e}") from e

        hits = []
        for item in raw_results:
            title = item.get("title")
            url = item.get("href") or item.get("url")
            if not title or not url:
                continue  # never fabricate a title/url that wasn't actually returned
            hits.append({"title": title, "url": url, "snippet": item.get("body") or None})
        return hits
