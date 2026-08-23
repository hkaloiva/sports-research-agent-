"""ContentProvider interface: retrieves the actual content of a URL.

This is the categorical opposite of a SearchProvider result — a
SearchResult (title/url/snippet) is a *pointer*; SourceContent is the
*actual page*. Extraction (sports_research/extraction/) must only ever
read from SourceContent.text, never from a SearchResult's snippet — see
docs/data-model.md § Search results vs. source content.
"""

from abc import ABC, abstractmethod


class ContentRetrievalError(Exception):
    """Raised when a page cannot legitimately be retrieved. Callers must
    record the source as inaccessible and continue — never fabricate
    content to fill the gap."""


def make_source_content(
    *,
    url: str,
    final_url: str,
    http_status,
    title,
    text,
    retrieval_method: str,
    retrieved_at: str,
    error=None,
) -> dict:
    """SourceContent record. `error` is set (and `text`/`title` are None)
    when retrieval failed but the caller still wants a record of the
    attempt — never claim a source was read if retrieval failed."""
    return {
        "url": url,
        "final_url": final_url,
        "http_status": http_status,
        "title": title,
        "text": text,
        "retrieval_method": retrieval_method,
        "retrieved_at": retrieved_at,
        "error": error,
    }


class ContentProvider(ABC):
    name = "unknown"

    @abstractmethod
    def fetch(self, url: str) -> dict:
        """Return a SourceContent dict (see make_source_content). Must
        not raise for an ordinary HTTP failure (404, timeout, etc.) —
        that's recorded in the returned dict's 'error'/'http_status' so
        the caller can continue with other sources. May raise
        ContentRetrievalError only for a setup/configuration problem
        (e.g. the retrieval method itself isn't available)."""
        raise NotImplementedError
