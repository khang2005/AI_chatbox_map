from __future__ import annotations

from typing import Any, Dict

from providers.gemini_provider import GeminiProvider


class IntentService:
    def __init__(self, gemini_provider: GeminiProvider) -> None:
        self.gemini_provider = gemini_provider

    def extract_intent(self, query: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        intent = self.gemini_provider.extract_intent(query, session_context)

        if "follow_up_to_previous" not in intent:
            intent["follow_up_to_previous"] = False

        if "follow_up_mode" not in intent:
            intent["follow_up_mode"] = "none"

        if "selected_index" not in intent:
            intent["selected_index"] = None

        return intent
