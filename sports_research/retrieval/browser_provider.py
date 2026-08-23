"""BrowserContentProvider: local Playwright rendering, for pages that
require JavaScript execution to show their content. Optional — the
application must work without it (see docs/retrieval.md § FREE/LOCAL vs
OPTIONAL). Not used for every page; ResearchEngine only falls back to
this when the plain HTTP fetch looks like it returned little/no content.

Playwright's browser binaries are a separate, sizeable download
(`playwright install chromium`) not performed automatically by this
module or by this build — see docs/configuration.md.
"""

from datetime import datetime, timezone

from .base import ContentProvider, make_source_content
from .http_provider import USER_AGENT, extract_main_text


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def browser_available() -> bool:
    """True only if both the playwright package AND a downloaded browser
    binary are present. Never raises."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False


class BrowserContentProvider(ContentProvider):
    name = "browser"

    def __init__(self, timeout_ms: int = 20000):
        self.timeout_ms = timeout_ms

    def fetch(self, url: str) -> dict:
        retrieved_at = _now_iso()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            return make_source_content(
                url=url, final_url=url, http_status=None, title=None, text=None,
                retrieval_method=self.name, retrieved_at=retrieved_at,
                error=f"playwright not installed: {e}",
            )

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    page = browser.new_page(user_agent=USER_AGENT)
                    response = page.goto(url, timeout=self.timeout_ms, wait_until="networkidle")
                    html = page.content()
                    final_url = page.url
                    status = response.status if response else None
                finally:
                    browser.close()
        except Exception as e:
            return make_source_content(
                url=url, final_url=url, http_status=None, title=None, text=None,
                retrieval_method=self.name, retrieved_at=retrieved_at, error=str(e),
            )

        if status is not None and status >= 400:
            return make_source_content(
                url=url, final_url=final_url, http_status=status, title=None, text=None,
                retrieval_method=self.name, retrieved_at=retrieved_at, error=f"HTTP {status}",
            )

        title, text = extract_main_text(html)
        return make_source_content(
            url=url, final_url=final_url, http_status=status, title=title, text=text,
            retrieval_method=self.name, retrieved_at=retrieved_at, error=None,
        )
