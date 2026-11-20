"""Small text helpers shared by the checks."""
from __future__ import annotations

import re
import unicodedata

_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def fold(s: str) -> str:
    """Lower case, no accents, sharp s written out: for matching, never for display."""
    return strip_accents(unicodedata.normalize("NFKC", s).casefold().replace("ß", "ss"))


def tokens(s: str) -> list[str]:
    """Words as written (accents and case kept), with an inner apostrophe kept: l'eau, don't."""
    return _WORD.findall(unicodedata.normalize("NFC", s))


def folded_tokens(s: str) -> list[str]:
    return [fold(t) for t in tokens(s)]
