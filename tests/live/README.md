# Live smoke tests

These are **not** part of the normal test suite (`python3 -m unittest
discover` never touches this directory — nothing here is named
`test_*.py`, and unittest's default discovery pattern skips it). They
require real internet access and are meant to be run **on your own
machine**, not inside this development sandbox.

## Why they can't run in this Claude Code sandbox

Confirmed directly, not assumed: outbound HTTPS to arbitrary external
domains (including a neutral control, `example.com`) returns `403` from
this sandbox's egress proxy — for raw `curl`, for the `WebFetch` tool,
and for plain Python `requests`. This is a sandbox-level network policy,
not a limitation of the code in `sports_research/`. See
`docs/limitations.md` for the full history of this finding across Steps
6–8 of this project. Per the sandbox's own guidance ("do not retry
organization policy denials"), this was confirmed once and not retried.

## Running them yourself

```bash
cd sports-research-agent
pip install -r requirements.txt
bash tests/live/run_live_smoke_tests.sh
```

This runs the CLI exactly as an end user would, for the two scenarios
the build spec calls out by name:

1. **`"Find every Arsenal Premier League result from the 2003/04 season."`**
2. **`"Find the results of the 2015 Street League Skateboarding competitions."`**
   — the second is the one that actually proves the system isn't secretly
   football-specific, since it exercises the placement-based extraction
   path (`extraction/deterministic.py`'s `extract_placement_event`)
   instead of the two-participant score-line path.

For each, the script reports exactly what the CLI itself reports:
searches performed, sources found, sources successfully retrieved,
records extracted, records validated, duplicates, discrepancies,
unresolved records, and the output file paths. It does not fabricate a
result if internet access fails — a failed run shows up as a genuine
CLI error/empty-results report, not a crafted success.
