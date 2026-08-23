"""PyInstaller entry point for the sports-research Windows executable.

Not a new feature — this just gives PyInstaller's static analyzer a
plain script to target (it can't target `python -m sports_research.cli`
directly). See docs/configuration.md § Windows executable.
"""

from sports_research.cli import main

if __name__ == "__main__":
    main()
