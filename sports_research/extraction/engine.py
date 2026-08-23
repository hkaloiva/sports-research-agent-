"""ExtractionEngine: DeterministicExtractor (always available) + an
optional local LLM assist (only when explicitly enabled AND a local
Ollama server is reachable). The deterministic extractor is always the
baseline — nothing here requires the optional path, and its absence
never crashes the application (just means some harder pages go
unextracted, reported honestly rather than silently)."""

from dataclasses import dataclass, field

from . import deterministic
from .local_llm import DEFAULT_MODEL, OptionalLocalLLMExtractor


@dataclass
class ExtractionOutcome:
    records: list = field(default_factory=list)
    ambiguous: list = field(default_factory=list)
    used_local_llm: bool = False
    capability_note: str = ""


class ExtractionEngine:
    def __init__(self, use_local_llm: bool = False, llm_model: str = DEFAULT_MODEL):
        self.use_local_llm = use_local_llm
        self._llm = OptionalLocalLLMExtractor(model=llm_model) if use_local_llm else None

    def extract_two_participant(self, text: str, **context) -> ExtractionOutcome:
        result = deterministic.extract_two_participant_events(text, **context)
        outcome = ExtractionOutcome(records=result.records, ambiguous=result.ambiguous)

        if result.records:
            return outcome  # deterministic extraction already succeeded; never probe the LLM

        if not self.use_local_llm:
            return outcome  # nothing found, and LLM assist isn't enabled

        if not self._llm.available():
            outcome.capability_note = "local LLM extraction was enabled but no Ollama server is reachable; used deterministic extraction only"
            return outcome

        # Deterministic extraction found nothing usable; ask the local
        # model to reformat the page into the exact 'DATE:' + 'Name X-Y
        # Name' lines deterministic.extract_two_participant_events()
        # already understands, then re-run that same, already-tested
        # parser on its output rather than trusting a new, unvalidated
        # LLM-output parser.
        prompt = (
            "From the following web page text, list every match/result you can find, "
            "using EXACTLY this format and nothing else: a line 'YYYY-MM-DD:' introducing "
            "a date, followed by one line per match played that date in the form "
            "'Name1 X-Y Name2' (plain integers X and Y, Name1 listed as the home side). "
            "If you cannot confidently determine a field for a match, omit that match "
            "entirely rather than guessing.\n\n"
            f"PAGE TEXT:\n{text[:8000]}"
        )
        try:
            raw_response = self._llm.extract_raw(prompt)
        except Exception as e:
            outcome.capability_note = f"local LLM call failed ({e}); used deterministic extraction only"
            return outcome

        parsed = deterministic.extract_two_participant_events(raw_response, **context)
        outcome.records = parsed.records
        outcome.ambiguous = parsed.ambiguous
        outcome.used_local_llm = True
        outcome.capability_note = "records extracted with local LLM assist (Ollama) after deterministic extraction found nothing"
        return outcome

    def extract_placement(self, text: str, **context) -> ExtractionOutcome:
        result = deterministic.extract_placement_event(text, **context)
        return ExtractionOutcome(records=result.records, ambiguous=result.ambiguous)
