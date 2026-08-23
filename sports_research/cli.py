"""CLI entry point.

    sports-research "Find every Arsenal Premier League result from 2003/04"
    sports-research --output csv --output-dir out "..."
    sports-research               # interactive mode

Runs entirely locally; the default configuration requires no paid API
key (see docs/configuration.md).
"""

import sys
from pathlib import Path

import click

from sports_research.config import Config
from sports_research.export.csv_export import export_csv
from sports_research.export.json_export import export_json
from sports_research.export.xlsx_export import export_xlsx
from sports_research.reporting.report import render_report
from sports_research.research.factory import build_research_engine


def _run_and_report(query: str, output_formats: list, output_dir: Path):
    engine = build_research_engine(Config)
    outcome = engine.run(query)

    for line in outcome.stage_log:
        click.echo(line)

    click.echo()
    click.echo(render_report(outcome))

    if outcome.clarification_needed or outcome.error:
        return outcome

    output_dir.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in query.lower())[:60].strip("_") or "research"

    if "csv" in output_formats:
        path = output_dir / f"{slug}.csv"
        export_csv(outcome.records, path)
        click.echo(f"\nWrote {path}")
    if "json" in output_formats:
        path = output_dir / f"{slug}.json"
        export_json(outcome, path)
        click.echo(f"Wrote {path}")
    if "xlsx" in output_formats:
        path = output_dir / f"{slug}.xlsx"
        export_xlsx(outcome, path)
        click.echo(f"Wrote {path}")

    return outcome


@click.command()
@click.argument("query", required=False)
@click.option("--output", "outputs", multiple=True, type=click.Choice(["csv", "json", "xlsx"]),
              default=("json",), help="Output format(s); repeatable.")
@click.option("--output-dir", type=click.Path(path_type=Path), default=None, help="Directory to write exports into.")
def main(query, outputs, output_dir):
    output_dir = output_dir or Config.OUTPUT_DIR

    if query:
        outcome = _run_and_report(query, list(outputs), output_dir)
        sys.exit(1 if (outcome.clarification_needed or outcome.error) else 0)

    click.echo("Sports Research Agent — interactive mode. Ctrl-C to exit.")
    while True:
        try:
            query = click.prompt("\nResearch request", default="", show_default=False)
        except (KeyboardInterrupt, EOFError):
            click.echo("\nGoodbye.")
            return
        if not query.strip():
            continue
        _run_and_report(query, list(outputs), output_dir)


if __name__ == "__main__":
    main()
