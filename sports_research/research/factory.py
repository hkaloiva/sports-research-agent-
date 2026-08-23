"""Builds a ResearchEngine wired from Config — the one place that turns
config settings into concrete provider instances."""

from sports_research.cache.store import CachedContentProvider, CachedSearchProvider, CacheStore
from sports_research.config import Config
from sports_research.extraction.engine import ExtractionEngine
from sports_research.retrieval.browser_provider import BrowserContentProvider, browser_available
from sports_research.retrieval.http_provider import HTTPContentProvider
from sports_research.search.base import FallbackSearchProvider
from sports_research.search.duckduckgo_provider import DuckDuckGoSearchProvider
from sports_research.search.wikipedia_provider import WikipediaSearchProvider
from sports_research.validation.completeness import check_completeness  # noqa: F401 (re-exported for convenience)
from .engine import ResearchEngine

_SEARCH_PROVIDER_CLASSES = {
    "duckduckgo": DuckDuckGoSearchProvider,
    "wikipedia": WikipediaSearchProvider,
}


def build_search_provider(config: Config = Config):
    names = [n.strip() for n in config.SEARCH_PROVIDER.split(",") if n.strip()]
    providers = [_SEARCH_PROVIDER_CLASSES[n]() for n in names if n in _SEARCH_PROVIDER_CLASSES]
    if not providers:
        providers = [DuckDuckGoSearchProvider()]
    provider = providers[0] if len(providers) == 1 else FallbackSearchProvider(providers)
    if config.CACHE_ENABLED:
        provider = CachedSearchProvider(provider, CacheStore(config.CACHE_DIR, config.CACHE_TTL_SECONDS))
    return provider


def build_content_provider(config: Config = Config):
    provider = HTTPContentProvider(timeout=config.REQUEST_TIMEOUT)
    if config.USE_BROWSER_FALLBACK and browser_available():
        # Not composed as a generic fallback chain here (JS-rendering is
        # expensive) — see docs/retrieval.md for the "only when the plain
        # HTTP fetch looks thin" policy a future ResearchEngine revision
        # could implement. For now this flag simply prefers the browser
        # provider outright when explicitly enabled and available.
        provider = BrowserContentProvider()
    if config.CACHE_ENABLED:
        provider = CachedContentProvider(provider, CacheStore(config.CACHE_DIR, config.CACHE_TTL_SECONDS))
    return provider


def build_research_engine(config: Config = Config) -> ResearchEngine:
    search_provider = build_search_provider(config)
    content_provider = build_content_provider(config)
    extraction_engine = ExtractionEngine(use_local_llm=config.OLLAMA_ENABLED, llm_model=config.OLLAMA_MODEL)
    return ResearchEngine(
        search_provider, content_provider, extraction_engine,
        max_sources_to_fetch=config.MAX_SOURCES_TO_FETCH,
    )
