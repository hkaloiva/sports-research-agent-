"""OptionalLocalLLMExtractor: an optional, local-only extension point for
extraction the deterministic patterns can't handle. Never required —
the application must work fully without it (see the build spec's
"LOCAL AI — OPTIONAL ONLY" section).

Uses Ollama (https://ollama.com) if it's installed and running locally —
never a cloud API, never a paid subscription. Does not download any
model automatically; the user must have already pulled one
(`ollama pull <model>`) — this module only checks for and talks to an
already-running local Ollama server.
"""

DEFAULT_MODEL = "llama3.1"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


def ollama_available(base_url: str = DEFAULT_OLLAMA_URL, timeout: float = 1.0) -> bool:
    """True only if a local Ollama server is actually reachable right
    now. Never raises."""
    try:
        import requests
        response = requests.get(f"{base_url}/api/tags", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


class OptionalLocalLLMExtractor:
    """Not a subclass of any required interface — this is an optional
    add-on the ExtractionEngine calls only when explicitly enabled AND
    a local Ollama server is actually reachable."""

    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_OLLAMA_URL, timeout: float = 60.0):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def available(self) -> bool:
        return ollama_available(self.base_url, timeout=1.0)

    def extract_raw(self, prompt: str) -> str:
        """Sends `prompt` to the local Ollama server and returns its raw
        text response. Callers remain responsible for parsing/validating
        the result — this module makes no claim the model's output is
        accurate, and nothing built on top of it should treat that output
        as ground truth without the same validation every other record
        goes through (validation/schema_validation.py)."""
        import requests
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "")
