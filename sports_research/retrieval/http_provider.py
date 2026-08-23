"""HTTPContentProvider: normal HTTP retrieval for static pages.

Respects robots.txt (never fetches a URL disallowed for our User-Agent),
uses a real identifying User-Agent, and never attempts to bypass
authentication, paywalls, or CAPTCHAs — a blocked/restricted page is
recorded as inaccessible, not worked around.
"""

import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import ContentProvider, make_source_content

USER_AGENT = "SportsResearchAgent/0.1 (local research tool; contact: local-user@example.invalid)"

_robots_cache = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _robots_allows(url: str, timeout: float) -> bool:
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in _robots_cache:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(urljoin(origin, "/robots.txt"))
        try:
            parser.read()
        except OSError:
            # robots.txt unreachable: fail open (most sites without a
            # reachable robots.txt intend no restriction), but this is
            # a real judgment call worth documenting — see docs/limitations.md.
            parser = None
        _robots_cache[origin] = parser
    parser = _robots_cache[origin]
    return True if parser is None else parser.can_fetch(USER_AGENT, url)


def extract_main_text(html: str):
    """Best-effort main-content extraction: strip script/style/nav/footer/
    header/aside/form, return visible text. Deliberately simple (no
    heuristic boilerplate-detection library) — good enough for structured
    stats pages and articles, weaker on heavily templated pages. See
    docs/retrieval.md § Known limitations."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    text = soup.get_text(separator="\n", strip=True)
    return title, text


class HTTPContentProvider(ContentProvider):
    name = "http"

    def __init__(self, timeout: float = 15.0, respect_robots: bool = True):
        self.timeout = timeout
        self.respect_robots = respect_robots

    def fetch(self, url: str) -> dict:
        retrieved_at = _now_iso()

        if self.respect_robots:
            try:
                allowed = _robots_allows(url, self.timeout)
            except Exception:
                allowed = True  # see _robots_allows' fail-open note
            if not allowed:
                return make_source_content(
                    url=url, final_url=url, http_status=None, title=None, text=None,
                    retrieval_method=self.name, retrieved_at=retrieved_at,
                    error="disallowed by robots.txt",
                )

        try:
            import requests
        except ImportError as e:
            return make_source_content(
                url=url, final_url=url, http_status=None, title=None, text=None,
                retrieval_method=self.name, retrieved_at=retrieved_at,
                error=f"'requests' package not installed: {e}",
            )

        try:
            response = requests.get(url, timeout=self.timeout, headers={"User-Agent": USER_AGENT})
        except requests.RequestException as e:
            return make_source_content(
                url=url, final_url=url, http_status=None, title=None, text=None,
                retrieval_method=self.name, retrieved_at=retrieved_at, error=str(e),
            )

        final_url = response.url
        if response.status_code >= 400:
            return make_source_content(
                url=url, final_url=final_url, http_status=response.status_code, title=None, text=None,
                retrieval_method=self.name, retrieved_at=retrieved_at,
                error=f"HTTP {response.status_code}",
            )

        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type and "text" not in content_type:
            return make_source_content(
                url=url, final_url=final_url, http_status=response.status_code, title=None, text=None,
                retrieval_method=self.name, retrieved_at=retrieved_at,
                error=f"unsupported content-type: {content_type or 'unknown'}",
            )

        title, text = extract_main_text(response.text)
        return make_source_content(
            url=url, final_url=final_url, http_status=response.status_code, title=title, text=text,
            retrieval_method=self.name, retrieved_at=retrieved_at, error=None,
        )
