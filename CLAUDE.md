# Sports Research Agent — working rules for Claude

Standalone, zero-cost-by-default sports research CLI/web app. Read this
before making changes — it captures rules and hard-won lessons from this
project's build, not just a description of what the code does.

## Non-negotiable design rules

- **Zero mandatory paid dependency.** No Claude/OpenAI/Anthropic API key,
  no paid search/scraping subscription required for the default
  configuration. Free, key-less services only (DuckDuckGo via `ddgs`,
  plain HTTP retrieval, Wikipedia's search API). Playwright (browser
  rendering) and an Ollama local LLM assist are genuinely optional extras
  — the app must keep working fully without either. Never make a new
  feature require a paid key by default.
- **Never fabricate.** No invented source, no invented record, no
  invented "found N results" — see `docs/limitations.md` and
  `docs/research-request.md` § the whole `source`/`basis` provenance
  model. A blocked or failed retrieval is reported as failed
  (`http_error`, etc.), never silently skipped or faked. Result counts
  are framed as estimates, never claims. This rule governs the codebase
  itself AND how you report your own work in this project — verify
  claims (tests passing, a build succeeding) before stating them; don't
  guess and call it done.
- **Deterministic, rule-based request understanding — not an LLM.**
  `sports_research/research/normalizer.py` and `planner.py` are regex +
  lookup-table based on purpose (see their own docstrings). An
  unresolved ambiguity becomes `needs_clarification`, never a guess.
  When you find a gap here (see "Real bugs found so far" below), fix the
  rule, don't reach for an LLM call as a shortcut.

## Testing discipline

- Run `python3 -m unittest discover` after every change, before saying
  something works. 213 tests as of this writing — grew from 205 as real
  bugs were found and fixed with regression tests, not just patched.
- When you fix a bug found via actually running the app (not
  theoretical), add a test that reproduces the exact real input that
  exposed it, with a comment naming what was actually observed. See
  `tests/sports_research/research/test_normalizer.py` and
  `tests/test_search_plan.py` for the pattern.

## Windows executable — real gotchas already paid for

`.github/workflows/build-windows.yml` builds `sports-research.exe` via
PyInstaller. This **cannot be cross-compiled from Linux/macOS** — it
must run on a real `windows-latest` GitHub Actions runner, which is why
this can't be built or tested in a Claude Code sandbox. The workflow
smoke-tests the built exe on that same real Windows runner before
treating a build as good. Lessons already learned the hard way — don't
rediscover these:

- GitHub Actions' `pwsh` step runner fails the *step* whenever the last
  native command's `$LASTEXITCODE` is nonzero, **regardless of your own
  script's checks** — if a step intentionally invokes something that
  exits nonzero and then verifies that was correct, it must explicitly
  `exit 0` afterward or the step is reported as failed anyway.
- Windows defaults redirected/piped stdout to the legacy console
  codepage, not UTF-8 — this mangles non-ASCII characters (em-dashes
  garbled to `�`). `packaging/entrypoint.py` reconfigures
  stdout/stderr to UTF-8 for exactly this reason; don't remove it.
- The release-tag trigger matches both `v*` and bare `X.Y.Z` — a real
  user typed a tag without the `v` prefix and the build silently never
  ran. Keep both patterns if you touch `on.push.tags`.
- The workflow needs `permissions: contents: write` explicitly — this
  repo's default `GITHUB_TOKEN` is read-only, and omitting this makes
  `gh release upload`/`create` fail with `HTTP 403: Resource not
  accessible by integration`.
- The release-attach step tries `gh release upload` first, falling back
  to `gh release create` — because a tag published via GitHub's web UI
  (the no-git-required path) already has an empty Release before the
  workflow runs, while a `git push` of a tag does not.

## GitHub access from a Claude Code session — real limits

Confirmed repeatedly, not assumed: a session here can push commits to an
existing branch, but **cannot** create a new repository, push or delete
a git tag, or delete a branch — all fail with `HTTP 403: Resource not
accessible by integration`, whether via git directly or the GitHub API/
MCP tools. Any of those three actions needs a human doing it via
GitHub's web UI. Don't retry these hoping for a different result; tell
the user what needs a manual click and why.

A `workflow_dispatch` run (no tag needed) still works and still uploads
a downloadable Actions artifact — useful for validating a fix, or as a
release-free way to get a build to the user, when a tagged Release isn't
available yet or isn't wanted.

## Repo history note

This project used to live as a subdirectory inside a different,
unrelated repo (`bg-stremio-addon`, a Stremio addon). It was moved out
into this standalone repo — don't be surprised by anything in old
commit messages that references that.
