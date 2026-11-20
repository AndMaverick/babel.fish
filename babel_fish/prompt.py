"""The prompts, built deterministically from the profile, the glossary and the verifier's findings. The same inputs give the same bytes."""
from __future__ import annotations

from .glossary import Glossary
from .profiles import Profile
from .violations import Violation


def system_prompt(profile: Profile, glossary: Glossary | None = None, spans: int = 0) -> str:
    lines = [f"You are a professional translator and localisation editor. Translate the user's text into {profile.name}. "
             "Reply with the translation only: no preamble, no notes, no quotation marks around it."]
    lines += profile.instructions()
    if spans:
        lines.append(f"The text contains {spans} protected token(s) written ⟦1⟧ to ⟦{spans}⟧. Keep each one exactly as written, once, in the right place.")
    if glossary and glossary.terms:
        lines.append("Required terminology: " + "; ".join(f'"{s}" must be "{t}"' for s, t in glossary.terms) + ".")
    if glossary and glossary.keep:
        lines.append("Do not translate or alter these names: " + ", ".join(f'"{k}"' for k in glossary.keep) + ".")
    lines.append("Do not add, drop or change any number, date, name or claim.")
    return "\n".join(lines)


def repair_prompt(source: str, previous: str, problems: list[Violation]) -> str:
    listed = "\n".join(f"- {p.message}" for p in problems)
    return (f"Your previous translation has problems:\n{listed}\n\nSource text:\n{source}\n\nYour previous translation:\n{previous}\n\n"
            "Reply with a corrected translation only.")
