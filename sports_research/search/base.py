"""SearchProvider interface.

A SearchProvider.search(query) returns raw hits shaped exactly like the
`backend` callable Step 6's search.py already expects
(list[{"title": str, "url": str, "snippet": str|None}]) — so
build_search_execution() from the top-level search.py module (dedup by
exact URL, query_used tracking, MalformedSearchHitError on a fabricated-
looking hit) is reused unchanged rather than reimplemented here.
"""

from abc import ABC, abstractmethod


class SearchProviderError(Exception):
    """Raised when a provider cannot complete a search (network error,
    library unavailable, rate-limited, etc.) — never silently returns a
    fabricated empty/fake result set."""


class SearchProvider(ABC):
    name = "unknown"

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list:
        """Return raw hits: [{"title": str, "url": str, "snippet": str|None}, ...].
        Raises SearchProviderError on failure — never fabricates a result."""
        raise NotImplementedError


class FallbackSearchProvider(SearchProvider):
    """Tries providers in order; falls through to the next on failure.
    This is the 'gracefully handle search failure' + multi-provider
    architecture the build spec asks for."""

    def __init__(self, providers: list):
        if not providers:
            raise ValueError("FallbackSearchProvider needs at least one provider")
        self.providers = providers
        self.name = "fallback(" + "+".join(p.name for p in providers) + ")"

    def search(self, query: str, max_results: int = 10) -> list:
        errors = []
        for provider in self.providers:
            try:
                return provider.search(query, max_results=max_results)
            except SearchProviderError as e:
                errors.append(f"{provider.name}: {e}")
        raise SearchProviderError(f"all providers failed for query {query!r}: {'; '.join(errors)}")
