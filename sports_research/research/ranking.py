"""Source prioritization/ranking (SOURCE PRIORITISATION in the build
spec). Classifies a URL into a source_type using domain heuristics, then
ranks candidate sources by that type's priority — official/structured
sources first, news articles and raw search-engine listings last.

A domain-heuristic classifier is inherently incomplete for the long tail
of the web — see docs/research-workflow.md § Known limitations. Nothing
downstream trusts the classification as ground truth; it only orders
which sources get fetched/extracted first.
"""

from urllib.parse import urlsplit

# Ordered most-preferred-first, matching planner.py's SOURCE_TYPES policy (Step 5).
SOURCE_TYPE_PRIORITY = [
    "statistical_database",
    "official_competition_source",
    "official_club_source",
    "sports_reference_site",
    "news_article",
    "search_engine_result",
    "other",
]

_STATISTICAL_DATABASE_DOMAINS = {"fbref.com", "sports-reference.com", "worldfootball.net", "espn.com"}
_OFFICIAL_COMPETITION_DOMAINS = {
    "premierleague.com", "fifa.com", "uefa.com", "formula1.com", "wimbledon.com",
    "atptour.com", "wtatennis.com", "streetleague.com",
}
_REFERENCE_DOMAINS = {"en.wikipedia.org", "wikipedia.org"}
_NEWS_DOMAINS = {"bbc.co.uk", "bbc.com", "skysports.com", "theguardian.com", "espn.com", "reuters.com"}


def domain_of(url: str) -> str:
    hostname = urlsplit(url).hostname
    return hostname.lower() if hostname else ""


def classify_source_type(url: str, participant_names: list = None) -> str:
    domain = domain_of(url)
    if domain in _STATISTICAL_DATABASE_DOMAINS:
        return "statistical_database"
    if domain in _OFFICIAL_COMPETITION_DOMAINS:
        return "official_competition_source"
    if domain in _REFERENCE_DOMAINS:
        return "sports_reference_site"
    if domain in _NEWS_DOMAINS:
        return "news_article"
    for name in participant_names or []:
        slug = name.lower().replace(" ", "")
        if slug and slug in domain.replace("-", "").replace(".", ""):
            return "official_club_source"
    return "other"


def rank_sources(urls: list, participant_names: list = None) -> list:
    """Returns `urls` sorted by source_type priority (most preferred
    first), stable within a tier (original relative order preserved)."""
    priority_index = {t: i for i, t in enumerate(SOURCE_TYPE_PRIORITY)}
    return sorted(urls, key=lambda u: priority_index[classify_source_type(u, participant_names)])
