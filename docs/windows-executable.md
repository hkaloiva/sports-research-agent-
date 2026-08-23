# Windows executable

A packaged build of the `sports-research` CLI for Windows, so a user
doesn't need Python or `pip install` — download, unzip, run.

## Why this can't be built locally in this environment

PyInstaller (and equivalent packagers) must run **on the target OS** —
there is no supported way to cross-compile a native Windows `.exe` from
a Linux sandbox. The build therefore runs on GitHub Actions'
`windows-latest` runner (`.github/workflows/build-windows.yml`), which
is a real Windows machine, not simulated. That same workflow runs a
smoke test against the freshly built `.exe` *on that Windows runner*
before treating the build as good — `--help`, an ambiguous offline
query (checks the bundled schema/config actually work, no network
needed), and a direct check that `event_result.schema.json` was actually
included in the bundle. The build is not published/released unless all
of that passes on real Windows.

## What's bundled, and why

The `sports-research` CLI's actual runtime dependency graph (verified by
grepping the codebase, not assumed) is: the `sports_research/` package,
two stdlib-only sibling modules at the repo root (`planner.py`,
`search.py` — Steps 5/6), and `schema/event_result.schema.json`. The
build (`--onedir`, `--paths .`, `--add-data "schema;schema"`) bundles
exactly this — see `packaging/entrypoint.py` for the PyInstaller target
script.

## Getting the build

1. **GitHub Release** (recommended, no git required): a tag matching
   `v*` (e.g. `v0.1.0`) triggers a release build with the zip attached.
   You don't need `git` installed to create that tag — GitHub's web UI
   can create it for you:
   - Go to the repository's `Releases` page → "Draft a new release".
   - In "Choose a tag", type a new tag name (e.g. `v0.1.0`) — GitHub
     offers "Create new tag: ... on publish".
   - Leave "Target" on the default branch (or pick another branch/commit
     if you want a different one built).
   - Click "Publish release". Publishing creates the tag, which fires
     the same `push: tags:` trigger a `git push` of that tag would —
     the workflow builds and smoke-tests on real Windows, then uploads
     the zip onto that same Release automatically.
   - Refresh the Release page once the workflow run finishes (Actions
     tab) and the zip will be attached as a downloadable asset.
2. **Manual trigger**: from the Actions tab, run "Build Windows
   executable" via `workflow_dispatch`, then download the
   `sports-research-windows` artifact from the completed run (requires
   being signed into GitHub; artifacts expire after GitHub's default
   retention period, unlike a Release asset).

## Using it

Unzip `sports-research-windows.zip` anywhere, then either:

- **From cmd/PowerShell** (recommended — lets you pass a query and see
  full output): `cd` into the unzipped folder and run
  `sports-research.exe "Find every Arsenal Premier League result from the 2003/04 season."`
- **Double-click `sports-research.exe`**: opens a console window in
  interactive mode (the same as running the CLI with no argument) —
  type your research request at the `Research request>` prompt.

Same zero-mandatory-cost behavior as the source install — see
`docs/configuration.md` and `docs/limitations.md`. This build only
packages the CLI, not the local web UI (`sports_research/webapp.py`) —
that still requires a source install (`pip install -e .`).
