# data/

- `raw/` — unprocessed data as pulled from sources, unmodified.
- `processed/` — cleaned and validated intermediate data.
- `exports/` — final structured output files (e.g. JSON/CSV).

Contents of these subfolders are gitignored (except `.gitkeep`) since
they hold generated data, not source code — with one exception:
`raw/test_results.json` is a committed test fixture (20 real historical
football results, manually compiled — not output from the research
pipeline, which doesn't exist yet). See
[`docs/data-schema.md`](../docs/data-schema.md) for the schema it follows.
