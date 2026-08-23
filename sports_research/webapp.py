"""Minimal local web UI. No visual design effort per the build spec —
functional only: a request box, a button, progress/status, a results
preview, and download links for CSV/JSON/XLSX.

Run: python3 -m sports_research.webapp
Then open http://localhost:5000
"""

import tempfile
import uuid
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, send_file, url_for

from sports_research.config import Config
from sports_research.export.csv_export import export_csv
from sports_research.export.json_export import export_json
from sports_research.export.xlsx_export import export_xlsx
from sports_research.reporting.report import render_report
from sports_research.research.factory import build_research_engine

app = Flask(__name__)
_RUNS = {}  # run_id -> (outcome, export_dir)

PAGE = """
<!doctype html>
<title>Sports Research Agent</title>
<h1>Sports Research Agent</h1>
<form method="post" action="/research">
  <input type="text" name="query" size="70" placeholder="Find every Arsenal Premier League result from the 2003/04 season."
         value="{{ query or '' }}">
  <button type="submit">Research</button>
</form>
{% if report %}
<pre>{{ report }}</pre>
{% endif %}
{% if run_id %}
<p>
  <a href="{{ url_for('download', run_id=run_id, fmt='csv') }}">Download CSV</a> |
  <a href="{{ url_for('download', run_id=run_id, fmt='json') }}">Download JSON</a> |
  <a href="{{ url_for('download', run_id=run_id, fmt='xlsx') }}">Download Excel</a>
</p>
{% endif %}
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/research", methods=["POST"])
def research():
    query = request.form.get("query", "").strip()
    if not query:
        return redirect(url_for("index"))

    engine = build_research_engine(Config)
    outcome = engine.run(query)
    report = render_report(outcome)

    run_id = None
    if not outcome.clarification_needed and not outcome.error:
        run_id = uuid.uuid4().hex
        export_dir = Path(tempfile.mkdtemp(prefix=f"sra_{run_id}_"))
        export_csv(outcome.records, export_dir / "results.csv")
        export_json(outcome, export_dir / "results.json")
        export_xlsx(outcome, export_dir / "results.xlsx")
        _RUNS[run_id] = export_dir

    return render_template_string(PAGE, query=query, report=report, run_id=run_id)


@app.route("/download/<run_id>/<fmt>")
def download(run_id, fmt):
    export_dir = _RUNS.get(run_id)
    if export_dir is None:
        return "Unknown or expired run.", 404
    filenames = {"csv": "results.csv", "json": "results.json", "xlsx": "results.xlsx"}
    if fmt not in filenames:
        return "Unknown format.", 400
    return send_file(export_dir / filenames[fmt], as_attachment=True)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
