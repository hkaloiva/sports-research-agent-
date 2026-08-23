"""Local, file-based cache for search results and retrieved page content —
reduces unnecessary repeat network requests and speeds up repeated
research on the same query/URL. Keyed by a hash of (kind, key); each
entry records when it was cached so it can be invalidated by age.
"""

import hashlib
import json
import time
from pathlib import Path


class CacheStore:
    def __init__(self, cache_dir, ttl_seconds: int = 24 * 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def _path_for(self, kind: str, key: str) -> Path:
        digest = hashlib.sha256(f"{kind}:{key}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{kind}_{digest}.json"

    def get(self, kind: str, key: str):
        path = self._path_for(kind, key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - entry["cached_at"] > self.ttl_seconds:
            return None
        return entry["value"]

    def set(self, kind: str, key: str, value) -> None:
        path = self._path_for(kind, key)
        path.write_text(json.dumps({"cached_at": time.time(), "key": key, "value": value}))

    def invalidate(self, kind: str, key: str) -> None:
        path = self._path_for(kind, key)
        if path.exists():
            path.unlink()

    def clear(self) -> None:
        for path in self.cache_dir.glob("*.json"):
            path.unlink()


class CachedSearchProvider:
    """Wraps any SearchProvider with CacheStore-backed caching."""

    def __init__(self, provider, cache: CacheStore):
        self.provider = provider
        self.cache = cache
        self.name = f"cached({provider.name})"

    def search(self, query: str, max_results: int = 10) -> list:
        key = f"{query}|{max_results}"
        cached = self.cache.get("search", key)
        if cached is not None:
            return cached
        results = self.provider.search(query, max_results=max_results)
        self.cache.set("search", key, results)
        return results


class CachedContentProvider:
    """Wraps any ContentProvider with CacheStore-backed caching."""

    def __init__(self, provider, cache: CacheStore):
        self.provider = provider
        self.cache = cache
        self.name = f"cached({provider.name})"

    def fetch(self, url: str) -> dict:
        cached = self.cache.get("content", url)
        if cached is not None:
            return cached
        content = self.provider.fetch(url)
        if content["error"] is None:
            self.cache.set("content", url, content)
        return content
