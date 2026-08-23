# Retrieval

## FREE/LOCAL

- **`HTTPContentProvider`** (default) — `sports_research/retrieval/http_provider.py`.
  Plain `requests` GET + BeautifulSoup/lxml text extraction. Respects
  `robots.txt` (`urllib.robotparser`, cached per-origin) — a disallowed
  URL is never fetched, recorded as `error: "disallowed by robots.txt"`
  instead. Sends a real, identifying `User-Agent`. Never attempts to
  bypass authentication, paywalls, or CAPTCHAs.

## OPTIONAL

- **`BrowserContentProvider`** — `sports_research/retrieval/browser_provider.py`,
  local Playwright (Chromium), for pages needing JavaScript execution to
  show their content. Not used by default and not used for every page —
  `USE_BROWSER_FALLBACK=true` in `.env` enables it (see
  `docs/configuration.md`). `browser_available()` checks whether both the
  `playwright` package **and** a downloaded browser binary are present;
  never raises, never auto-downloads the (large) browser binary itself —
  that's a one-time `playwright install chromium` the user runs
  explicitly.

## What every fetch captures

`sports_research/retrieval/base.py`'s `make_source_content()`: `url`,
`final_url` (post-redirect), `http_status`, `title`, `text`,
`retrieval_method`, `retrieved_at`, `error`. **A failed fetch is recorded,
never silently dropped, and never claimed as a successful read** — every
call site checks `content["error"] is None` before treating `text` as
real page content.

## Known limitations

- **Main-content extraction is simple**, not a full boilerplate-removal
  heuristic engine (`extract_main_text()` just strips
  `script`/`style`/`nav`/`footer`/`header`/`aside`/`form` and takes
  remaining visible text). Works well for structured stats tables and
  article prose; weaker on heavily templated pages with lots of sidebar
  content mixed into the main area.
- **Unreachable `robots.txt` fails open** (treated as "no restriction")
  — a real, documented judgment call, not a silent default. Most sites
  without a reachable `robots.txt` genuinely don't intend to restrict
  crawling, but this is a heuristic, not a certainty.
- **`BrowserContentProvider` isn't composed as an automatic fallback**
  in `ResearchEngine` yet (e.g. "retry with the browser only if the plain
  HTTP fetch returned suspiciously little text") — currently it's an
  outright preference when `USE_BROWSER_FALLBACK=true`, not a smart
  per-page decision. A real limitation, not a design goal left unfinished
  by omission — documented here rather than silently.
