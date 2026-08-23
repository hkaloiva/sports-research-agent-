"""ResearchEngine: orchestrates the full pipeline.

USER REQUEST -> normalize -> plan -> search -> rank -> retrieve ->
extract -> validate -> dedup -> cross-source compare -> completeness ->
report -> export.

Every stage is implemented in its own module (normalizer.py, planner.py,
search/, ranking.py, retrieval/, extraction/, validation/) and called
from here — this file only orchestrates, it doesn't implement pipeline
logic itself, so each stage stays independently testable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import search as search_module  # top-level search.py (Step 6): dedup by exact URL, query_used tracking
from sports_research.extraction.engine import ExtractionEngine
from sports_research.models.source import make_source
from sports_research.research.normalizer import normalize_request
from sports_research.research.planner import AmbiguousRequestError, build_search_plan
from sports_research.research.ranking import classify_source_type, rank_sources
from sports_research.validation.completeness import check_completeness
from sports_research.validation.conflicts import classify_group
from sports_research.validation.dedup import group_duplicate_events
from sports_research.validation.schema_validation import validate_event_result


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ResearchOutcome:
    request: dict = None
    plan: dict = None
    search_execution: dict = None
    sources: list = field(default_factory=list)
    records: list = field(default_factory=list)
    validation_problems: dict = field(default_factory=dict)  # event_id -> [problems]
    duplicate_groups: list = field(default_factory=list)
    verification_by_group: list = field(default_factory=list)
    completeness: dict = None
    stage_log: list = field(default_factory=list)
    clarification_needed: bool = False
    clarification_questions: list = field(default_factory=list)
    error: str = None


class ResearchEngine:
    def __init__(self, search_provider, content_provider, extraction_engine: ExtractionEngine = None,
                 max_sources_to_fetch: int = 5, expected_count_lookup=None):
        self.search_provider = search_provider
        self.content_provider = content_provider
        self.extraction_engine = extraction_engine or ExtractionEngine(use_local_llm=False)
        self.max_sources_to_fetch = max_sources_to_fetch
        self.expected_count_lookup = expected_count_lookup  # optional callable(plan) -> int|None

    def _log(self, outcome: ResearchOutcome, step: int, total: int, message: str):
        outcome.stage_log.append(f"[{step}/{total}] {message}")

    def run(self, raw_query: str) -> ResearchOutcome:
        outcome = ResearchOutcome()
        total = 8

        self._log(outcome, 1, total, "Understanding request")
        outcome.request = normalize_request(raw_query)
        if outcome.request["status"] == "needs_clarification":
            outcome.clarification_needed = True
            outcome.clarification_questions = outcome.request["clarifications_needed"]
            return outcome

        try:
            outcome.plan = build_search_plan(outcome.request)
        except AmbiguousRequestError as e:
            outcome.error = str(e)
            return outcome

        self._log(outcome, 2, total, "Searching")
        backend = self._backend_from_provider()
        outcome.search_execution = search_module.build_search_execution(
            outcome.plan, backend, provider=self.search_provider.name, retrieved_at=_now_iso(),
        )

        participant_names = []
        for field_name in ("teams",):
            entry = outcome.plan["search_scope"].get(field_name)
            if entry:
                participant_names.extend(entry["value"])

        ranked_urls = rank_sources([r["url"] for r in outcome.search_execution["results"]], participant_names)
        results_by_url = {r["url"]: r for r in outcome.search_execution["results"]}

        self._log(outcome, 3, total, "Retrieving sources")
        fetched = []
        for url in ranked_urls[: self.max_sources_to_fetch]:
            content = self.content_provider.fetch(url)
            source_type = classify_source_type(url, participant_names)
            source = make_source(
                source_id=f"src_{len(outcome.sources) + 1}",
                title=results_by_url[url]["title"], url=url,
                retrieved_at=content["retrieved_at"],
                retrieval_status="ok" if content["error"] is None else "http_error",
                source_type=source_type,
            )
            outcome.sources.append(source)
            if content["error"] is None:
                fetched.append((source, content))

        self._log(outcome, 4, total, "Extracting results")
        constraints = outcome.request["constraints"]
        sport = constraints["sport"]["value"]
        competition = constraints["competition"]["value"] if "competition" in constraints else sport
        season = constraints.get("season", {}).get("value", "")
        has_named_participants = "teams" in constraints  # two-participant (team/head-to-head) style request
        extracted = []
        for source, content in fetched:
            text = content["text"] or ""
            if has_named_participants:
                outcome_ext = self.extraction_engine.extract_two_participant(
                    text, sport=sport, competition=competition, season=season,
                    source=source["title"], source_url=source["url"], source_accessed_at=source["retrieved_at"],
                )
            else:
                # No specific team/competitor named: this is a placement/
                # leaderboard-style request (e.g. a skateboarding contest
                # or a motorsport season) rather than a two-side score.
                event_name = constraints.get("event_name", {}).get("value", competition)
                event_date = constraints.get("date_from", {}).get("value") or f"{season}-01-01" if season else None
                if event_date is None:
                    continue  # no date to attach a placement-based event to; don't guess one
                outcome_ext = self.extraction_engine.extract_placement(
                    text, sport=sport, competition=competition, season=season,
                    event_name=event_name, date=event_date,
                    source=source["title"], source_url=source["url"], source_accessed_at=source["retrieved_at"],
                )
            extracted.extend(outcome_ext.records)
        outcome.records = extracted

        self._log(outcome, 5, total, "Validating")
        for record in outcome.records:
            problems = validate_event_result(record)
            if problems:
                outcome.validation_problems[record["event_id"]] = problems

        self._log(outcome, 6, total, "Checking duplicates")
        outcome.duplicate_groups = group_duplicate_events(outcome.records)

        self._log(outcome, 7, total, "Comparing sources")
        domain_by_url = {s["url"]: s["domain"] for s in outcome.sources}
        for group_indices in outcome.duplicate_groups:
            group_events = [outcome.records[i] for i in group_indices]
            group_domains = [domain_by_url.get(e["source_url"], "") for e in group_events]
            classification = classify_group(group_events, group_domains)
            outcome.verification_by_group.append({"indices": group_indices, **classification})
            for local_i, global_i in enumerate(group_indices):
                if local_i in classification["disagreeing_indices"] or local_i in classification["agreeing_indices"]:
                    outcome.records[global_i]["verification_status"] = classification["verification_status"]

        expected = self.expected_count_lookup(outcome.plan) if self.expected_count_lookup else None
        duplicate_count = sum(len(g) - 1 for g in outcome.duplicate_groups)
        outcome.completeness = check_completeness(
            found_count=len(outcome.records), duplicate_count=duplicate_count,
            unresolved_count=len(outcome.validation_problems), expected_count=expected,
        )

        self._log(outcome, 8, total, "Exporting")
        return outcome

    def _backend_from_provider(self):
        def backend(query: str):
            try:
                return self.search_provider.search(query)
            except Exception:
                return []  # search failure for one query: continue with the others, never fabricate hits
        return backend
