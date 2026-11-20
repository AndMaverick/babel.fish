"""Profiles: the instruction wording for each target language, tone and context, and the number format the language uses."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import BabelError

LANGUAGES = {"en": "English", "de": "German", "fr": "French", "es": "Spanish"}
TONES = ("formal", "casual")
CONTEXTS = ("general", "legal", "investor", "marketing", "technical", "pitch")
NUMBER_EXAMPLE = {"en": "1,234.56", "de": "1.234,56", "fr": "1 234,56 (narrow no-break space)", "es": "1.234,56"}

ADDRESS = {
    ("de", "formal"): 'Address the reader as "Sie" (capitalised) and never use "du" forms.',
    ("de", "casual"): 'Address the reader as "du" and never use the formal "Sie".',
    ("fr", "formal"): 'Address the reader as "vous" and never use "tu" forms.',
    ("fr", "casual"): 'Address the reader as "tu" and keep the register conversational.',
    ("es", "formal"): 'Address the reader as "usted" and never use "tú" forms.',
    ("es", "casual"): 'Address the reader as "tú" and keep the register conversational.',
    ("en", "formal"): "Write in formal English: no contractions, no slang.",
    ("en", "casual"): "Write in relaxed, conversational English; contractions are fine.",
}
CONTEXT = {
    "general": "Translate naturally and faithfully.",
    "legal": "Use precise legal terminology, keep sentence structure close to the source and avoid colloquial wording.",
    "investor": "Write for an investor audience: confident, precise and free of hype; keep every figure exact.",
    "marketing": "Write persuasive marketing copy that stays true to every claim and figure in the source.",
    "technical": "Use standard technical terminology of the target language and leave identifiers, commands and code unchanged.",
    "pitch": "Write bold, concise startup pitch language, without adding or dropping any claim or figure.",
}


@dataclass(frozen=True)
class Profile:
    language: str
    tone: str = "formal"
    context: str = "general"

    def __post_init__(self) -> None:
        if self.language not in LANGUAGES:
            raise BabelError(f"language must be one of {', '.join(LANGUAGES)}, got {self.language!r}")
        if self.tone not in TONES:
            raise BabelError(f"tone must be one of {', '.join(TONES)}, got {self.tone!r}")
        if self.context not in CONTEXTS:
            raise BabelError(f"context must be one of {', '.join(CONTEXTS)}, got {self.context!r}")

    @property
    def name(self) -> str:
        return LANGUAGES[self.language]

    def instructions(self) -> list[str]:
        return [ADDRESS[(self.language, self.tone)], CONTEXT[self.context],
                f"Write numbers the way {self.name} does (for example {NUMBER_EXAMPLE[self.language]}), without changing any value."]
