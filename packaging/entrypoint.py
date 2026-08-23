"""PyInstaller entry point for the sports-research Windows executable.

Not a new feature — this just gives PyInstaller's static analyzer a
plain script to target (it can't target `python -m sports_research.cli`
directly). See docs/configuration.md § Windows executable.
"""

import sys

# Windows defaults stdout/stderr to the legacy console codepage rather
# than UTF-8 whenever output isn't an interactive terminal (e.g.
# redirected to a file, or piped) — the report text's em-dashes come
# out as mojibake in that case. Confirmed on a real windows-latest CI
# run before adding this, not assumed.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from sports_research.cli import main

if __name__ == "__main__":
    main()
