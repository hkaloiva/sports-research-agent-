#!/bin/bash
# One-command setup for Linux/macOS. Creates a virtual environment,
# installs the application (which registers the `sports-research`
# command) and its zero-cost-by-default dependencies, then runs the
# test suite to confirm everything works.
#
# Windows: see the "Windows" section in README.md for the equivalent
# commands (this script itself requires bash).
set -euo pipefail
cd "$(dirname "$0")"

echo "== Creating virtual environment (.venv) =="
python3 -m venv .venv

echo "== Installing sports-research-agent + dependencies =="
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .

echo "== Running the test suite (no internet required) =="
.venv/bin/python3 -m unittest discover

echo
echo "Setup complete. Activate the environment with:"
echo "    source .venv/bin/activate"
echo "Then run, for example:"
echo "    sports-research \"Find every Arsenal Premier League result from the 2003/04 season.\""
