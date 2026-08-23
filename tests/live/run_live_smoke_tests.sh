#!/bin/bash
# Live smoke tests — REQUIRES REAL INTERNET ACCESS. Run on your own
# machine, not inside a network-restricted sandbox. See tests/live/README.md.
set -euo pipefail
cd "$(dirname "$0")/../.."

OUT_DIR="tests/live/output"
mkdir -p "$OUT_DIR"

echo "=== Live smoke test 1: Arsenal Premier League 2003/04 ==="
python3 -m sports_research.cli \
  --output csv --output json --output xlsx --output-dir "$OUT_DIR" \
  "Find every Arsenal Premier League result from the 2003/04 season." \
  | tee "$OUT_DIR/arsenal_2003_04.log"

echo
echo "=== Live smoke test 2: 2015 Street League Skateboarding (proves not football-specific) ==="
python3 -m sports_research.cli \
  --output csv --output json --output xlsx --output-dir "$OUT_DIR" \
  "Find the results of the 2015 Street League Skateboarding competitions." \
  | tee "$OUT_DIR/sls_2015.log"

echo
echo "Logs and exports written to $OUT_DIR/"
