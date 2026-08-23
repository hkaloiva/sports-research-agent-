# Configuration

Copy `.env.example` to `.env` and adjust if needed — **every default is
zero-cost**, no setting requires a paid API key. Loaded by
`sports_research/config.py` via `python-dotenv`.

| Setting | Default | FREE/LOCAL or OPTIONAL |
|---|---|---|
| `SEARCH_PROVIDER` | `duckduckgo,wikipedia` | FREE/LOCAL — both zero-cost, key-less |
| `REQUEST_TIMEOUT` | `15` (seconds) | — |
| `MAX_SOURCES_TO_FETCH` | `5` | — |
| `CACHE_ENABLED` | `true` | FREE/LOCAL — local disk only |
| `CACHE_DIR` | `data/cache` | — |
| `CACHE_TTL_SECONDS` | `86400` (1 day) | — |
| `USE_BROWSER_FALLBACK` | `false` | **OPTIONAL** — see below |
| `OLLAMA_ENABLED` | `false` | **OPTIONAL** — see below |
| `OLLAMA_MODEL` | `llama3.1` | — |
| `OLLAMA_URL` | `http://localhost:11434` | — |
| `OUTPUT_DIR` | `data/exports` | — |

## Optional: browser-based content retrieval (Playwright)

For pages requiring JavaScript execution. Not installed/downloaded
automatically:

```bash
pip install playwright   # or: pip install -e ".[browser]"
playwright install chromium
```

Then set `USE_BROWSER_FALLBACK=true`. Free, but Chromium's binary is a
real (~150MB+) download — that's why it's opt-in, not automatic.

## Optional: local LLM extraction assist (Ollama)

For pages the deterministic extractor can't parse. Install
[Ollama](https://ollama.com) (free, runs entirely locally, no cloud API),
then:

```bash
ollama pull llama3.1   # or any model you prefer
ollama serve            # if not already running
```

Then set `OLLAMA_ENABLED=true` (and `OLLAMA_MODEL` if not using
`llama3.1`). The application works fully without this — it's checked for
availability at request time and silently (but reportably) skipped if
Ollama isn't running.

## No setting here is a paid API key

Nothing in this file, `.env.example`, or `sports_research/config.py`
configures OpenAI, Anthropic, or any paid search/scraping service — none
is used anywhere in this codebase.
