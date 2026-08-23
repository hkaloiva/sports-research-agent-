# Search

## FREE/LOCAL

Both search providers are zero-cost, key-less, and legitimate:

- **`DuckDuckGoSearchProvider`** (default) — `sports_research/search/duckduckgo_provider.py`,
  via the `ddgs` package (MIT-licensed, actively maintained; formerly
  `duckduckgo-search`). No API key, no paid account, no CAPTCHA-gated
  flow, no bypassing of any access control.
- **`WikipediaSearchProvider`** (default fallback) — `sports_research/search/wikipedia_provider.py`,
  via Wikipedia/MediaWiki's own official, documented `action=query&list=search`
  API. Sends a real identifying `User-Agent`, per Wikimedia's API Usage
  Guidelines (see `docs/web-access-options.md`'s research). Narrower than
  general web search (wikipedia.org only) but often has exactly the
  structured historical-season content this application needs.

`SEARCH_PROVIDER=duckduckgo,wikipedia` (the default, see
`docs/configuration.md`) tries them in that order —
`FallbackSearchProvider` (`sports_research/search/base.py`) falls through
to the next provider on failure and only raises if every provider fails.
A single query's failure never crashes `ResearchEngine.run()` — it's
caught and treated as "this query found nothing," not a fatal error.

## Source prioritization

`sports_research/research/ranking.py` classifies each result into a
`source_type` and orders fetch priority (`SOURCE_TYPE_PRIORITY`):

1. `statistical_database` (e.g. fbref.com, sports-reference.com)
2. `official_competition_source` (e.g. premierleague.com, fifa.com, formula1.com)
3. `official_club_source` (heuristic: participant name found in the domain)
4. `sports_reference_site` (e.g. Wikipedia)
5. `news_article` (e.g. bbc.co.uk, theguardian.com)
6. `search_engine_result`
7. `other` (everything unclassified)

A domain-heuristic classifier is inherently incomplete for the long tail
of the web — this only decides *fetch order*, never which records are
trusted; that's `verification_status`'s job (`docs/validation.md`).

## Search results vs. source content

A `SearchProvider` result is `{title, url, snippet}` — a **pointer**,
never full page content. `snippet` is `None` when the provider didn't
supply one; never synthesized from anything else. Extraction only ever
reads `ContentProvider`-fetched text (`docs/retrieval.md`), never a
search snippet — the categorical distinction `docs/web-access-options.md`
identified as the most important thing to get right.
