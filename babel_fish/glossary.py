"""Glossaries: required terminology and names that must not be translated."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import BabelError
from .text import fold
from .violations import Violation


@dataclass(frozen=True)
class Glossary:
    terms: tuple[tuple[str, str], ...] = ()       # (source term, required target term)
    keep: tuple[str, ...] = ()                    # written exactly as in the source, in any language

    @classmethod
    def from_dict(cls, raw: object) -> Glossary:
        if not isinstance(raw, dict) or set(raw) - {"terms", "keep"}:
            raise BabelError('glossary: an object with "terms" (source to target) and "keep" (names that stay as they are)')
        terms = raw.get("terms", {})
        keep = raw.get("keep", [])
        if not isinstance(terms, dict) or not all(isinstance(k, str) and isinstance(v, str) and k and v for k, v in terms.items()):
            raise BabelError('glossary.terms: must map non-empty text to non-empty text')
        if not isinstance(keep, list) or not all(isinstance(k, str) and k for k in keep):
            raise BabelError("glossary.keep: must be a list of non-empty text")
        return cls(tuple(sorted(terms.items())), tuple(sorted(set(keep))))

    @classmethod
    def load(cls, path: str) -> Glossary:
        try:
            return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
        except OSError as e:
            raise BabelError(f"cannot read {path}: {e.strerror or e}") from None
        except json.JSONDecodeError as e:
            raise BabelError(f"{path} is not valid JSON: {e}") from None


def _present(term: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def check(source: str, output: str, g: Glossary) -> list[Violation]:
    out: list[Violation] = []
    fs, fo = fold(source), fold(output)
    for src, tgt in g.terms:
        if _present(fold(src), fs) and fold(tgt) not in fo:
            out.append(Violation("glossary", "error", f'"{src}" must be translated as "{tgt}"'))
    for name in g.keep:
        if _present(name, source) and name not in output:
            out.append(Violation("keep", "error", f'"{name}" must stay exactly as written'))
    return out
