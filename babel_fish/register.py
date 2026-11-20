"""Register checks: does the text address the reader the way the profile asks (Sie or du, vous or tu, usted or tú), and does English avoid
contractions and slang where the profile is formal.

These are word-list checks. They catch the common failures of a translation that ignored the requested tone and say nothing about style."""
from __future__ import annotations

import re

from .text import tokens
from .violations import Violation

DE_DU = {"du", "dich", "dir", "dein", "deine", "deinem", "deinen", "deiner", "deines", "euch"}
DE_SIE_CAP = {"Sie", "Ihnen", "Ihr", "Ihre", "Ihrem", "Ihren", "Ihrer", "Ihres"}
FR_TU = {"tu", "toi", "te", "ta", "tes"}
ES_TU = {"tú", "tu", "tus", "ti", "te", "contigo", "vosotros", "vosotras", "vuestro", "vuestra", "vuestros", "vuestras", "os"}
EN_SLANG = {"gonna", "wanna", "gotta", "kinda", "sorta", "yeah", "nope", "awesome", "guys", "hey", "lol", "stuff", "okay", "ok"}
_CONTRACTION = re.compile(r"\b\w+(?:n[’']t|[’'](?:re|ve|ll|d|m))\b", re.IGNORECASE)
_EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿]")
_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?")


def _sentence_start(text: str, pos: int) -> bool:
    before = text[:pos].rstrip(" \t\"“«(‘'")
    return before == "" or before[-1] in ".!?:\n…"


def _french_ton(low: list[str]) -> set[str]:
    """"ton" is the possessive "your" (tu-form) but also the noun "tone"; as a noun it follows a determiner ("le ton", "un ton", "ce ton")."""
    return {"ton" for i, t in enumerate(low) if t == "ton" and not (i and low[i - 1] in {"le", "un", "ce", "du", "au", "ton"})}


def check(text: str, lang: str, tone: str, context: str) -> list[Violation]:
    out: list[Violation] = []
    formal = tone == "formal"
    toks = tokens(text)
    low = [t.lower() for t in toks]
    if lang == "de":
        if formal:
            hits = sorted({t for t in low if t in DE_DU})
            if hits:
                out.append(Violation("register", "error", f"informal German address (du-forms) in a formal text: {', '.join(hits)}"))
        else:
            hit = sorted({m.group(0) for m in _WORD.finditer(text) if m.group(0) in DE_SIE_CAP and not _sentence_start(text, m.start())})
            if hit:
                out.append(Violation("register", "error", f"formal German address (Sie-forms) in a casual text: {', '.join(hit)}"))
    elif lang == "fr":
        if formal:
            hits = sorted({t for t in low if t in FR_TU or t.startswith("t'")} | _french_ton(low))
            if hits:
                out.append(Violation("register", "error", f"informal French address (tu-forms) in a formal text: {', '.join(hits)}"))
        elif "vous" in low:
            out.append(Violation("register", "warning", "vous in a casual French text (may be a plural you)"))
    elif lang == "es":
        if formal:
            hits = sorted({t for t in low if t in ES_TU})
            if hits:
                out.append(Violation("register", "error", f"informal Spanish address (tú-forms) in a formal text: {', '.join(hits)}"))
        elif "usted" in low:
            out.append(Violation("register", "warning", "usted in a casual Spanish text"))
    elif lang == "en" and (formal or context in ("legal", "investor")):
        c = sorted({m.group(0).lower() for m in _CONTRACTION.finditer(text)})
        if c:
            out.append(Violation("register", "error", f"contractions in a formal English text: {', '.join(c)}"))
        s = sorted({t for t in low if t in EN_SLANG})
        if s:
            out.append(Violation("register", "warning", f"informal words in a formal English text: {', '.join(s)}"))
    if (formal or context == "legal") and _EMOJI.search(text):
        out.append(Violation("register", "warning", "emoji in a formal text"))
    if context == "legal" and "!" in text:
        out.append(Violation("register", "warning", "exclamation mark in a legal text"))
    return out
