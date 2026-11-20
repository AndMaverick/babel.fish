"""Numbers in running text, read the way each language writes them, so a translation can be checked for changed values.

1.234,56 (German, Spanish), 1 234,56 (French), 1,234.56 (English) are the same value. Dates and times are compared as the integers they
contain, so 11/20/2026 and 20.11.2026 agree. Number words from two to a hundred count as the number they say. Percent signs, currency
symbols and unit words are ignored: only the value is compared."""
from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal

from .numwords import phrases_longest_first, table
from .text import fold

Key = Decimal | tuple[str, tuple[int, ...]]

_THOUSANDS = {"en": ",", "de": ".", "es": ".", "fr": "[   ]"}
_DECIMAL = {"en": ".", "de": ",", "es": ",", "fr": ","}
_DATE = re.compile(r"(?<![\d.,])(\d{1,4})([./-])(\d{1,2})\2(\d{1,4})(?![\d])")
_TIME = re.compile(r"(?<![\d.,:])(\d{1,2}):(\d{2})(?::(\d{2}))?(?![\d:])")
_TOKEN = re.compile("⟦\\d+⟧")


def _number_regex(lang: str) -> re.Pattern[str]:
    th = _THOUSANDS[lang] if lang == "fr" else re.escape(_THOUSANDS[lang])
    dec = re.escape(_DECIMAL[lang])
    return re.compile(rf"(?<![\w.,])(\d{{1,3}}(?:{th}\d{{3}})+(?:{dec}\d+)?|\d+(?:{dec}\d+)?)(?![\w])|(\d+)")


_REGEX = {k: _number_regex(k) for k in _THOUSANDS}


def parse_number(s: str, lang: str) -> Decimal:
    th, dec = _THOUSANDS[lang], _DECIMAL[lang]
    t = re.sub(th, "", s) if len(th) > 1 else s.replace(th, "")
    return Decimal(t.replace(dec, "."))


def _word_regex(lang: str) -> re.Pattern[str]:
    alt = "|".join(re.escape(p) for p in phrases_longest_first(lang))
    return re.compile(rf"(?<![a-z0-9])(?:{alt})(?![a-z0-9])")


_WORDS = {k: _word_regex(k) for k in _THOUSANDS}


def extract(text: str, lang: str) -> Counter[Key]:
    """The multiset of values written in ``text``, read with the conventions of ``lang`` (en, de, fr or es)."""
    lang = lang if lang in _THOUSANDS else "en"
    out: Counter[Key] = Counter()
    s = _TOKEN.sub(" ", text)

    def take(rx: re.Pattern[str], s: str, make: object) -> str:
        def sub(m: re.Match[str]) -> str:
            out[make(m)] += 1                                    # type: ignore[operator]
            return " " * len(m.group(0))
        return rx.sub(sub, s)

    s = take(_DATE, s, lambda m: ("date", tuple(sorted(int(m.group(i)) for i in (1, 3, 4)))))
    s = take(_TIME, s, lambda m: ("time", tuple(int(g) for g in m.groups() if g is not None)))
    for m in _REGEX[lang].finditer(s):
        out[parse_number(m.group(1), lang) if m.group(1) else Decimal(m.group(2))] += 1
    words = table(lang)
    f = re.sub(r"\s+", " ", fold(s))
    for m in _WORDS[lang].finditer(f):
        out[Decimal(words[m.group(0)])] += 1
    return out


def compare(source: Counter[Key], output: Counter[Key]) -> tuple[list[Key], list[Key]]:
    """(missing, added): values in the source that the output lacks, and values in the output that the source lacks."""
    missing = sorted((source - output).elements(), key=repr)
    added = sorted((output - source).elements(), key=repr)
    return missing, added


def show(key: Key) -> str:
    if isinstance(key, Decimal):
        return format(key.normalize(), "f")
    kind, parts = key
    return ("-".join if kind == "date" else ":".join)(str(p) for p in parts)
