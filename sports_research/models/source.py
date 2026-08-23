"""Source: a record describing one web source consulted during research,
stored separately from the EventResults it contributed to (per the
PROVENANCE section of the build spec)."""

from urllib.parse import urlsplit


def domain_of(url: str) -> str:
    hostname = urlsplit(url).hostname
    return hostname.lower() if hostname else ""


def make_source(
    *,
    source_id: str,
    title: str,
    url: str,
    retrieved_at: str,
    retrieval_status: str,
    source_type: str = "other",
) -> dict:
    """retrieval_status: 'ok' | 'http_error' | 'network_error' | 'blocked' | 'not_attempted'.
    source_type: one of the categories from docs/search.md's source ranking
    (official_competition_source, official_club_source, statistical_database,
    sports_reference_site, news_article, search_engine_result, other)."""
    return {
        "source_id": source_id,
        "title": title,
        "url": url,
        "domain": domain_of(url),
        "retrieved_at": retrieved_at,
        "retrieval_status": retrieval_status,
        "source_type": source_type,
    }
