"""Number words from 2 to 100 in English, German, French and Spanish, generated from rules and compared accent- and case-insensitively.

"one", "ein", "un", "uno" are left out on purpose: they are also articles, so reading them as the number 1 would invent numbers."""
from __future__ import annotations

from functools import cache

from .text import fold

EN_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
EN_TENS = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety"}

DE_UNITS = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"]
DE_TENS = {20: "zwanzig", 30: "dreißig", 40: "vierzig", 50: "fünfzig", 60: "sechzig", 70: "siebzig", 80: "achtzig", 90: "neunzig"}

FR_UNITS = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
FR_TENS = {20: "vingt", 30: "trente", 40: "quarante", 50: "cinquante", 60: "soixante"}

ES_UNITS = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve"]
ES_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
ES_TWENTIES = {20: "veinte", 21: "veintiuno", 22: "veintidós", 23: "veintitrés", 24: "veinticuatro", 25: "veinticinco", 26: "veintiséis",
               27: "veintisiete", 28: "veintiocho", 29: "veintinueve"}


def _en(n: int) -> list[str]:
    if n < 20:
        return [EN_UNITS[n]]
    if n == 100:
        return ["one hundred", "hundred", "a hundred"]
    tens, unit = divmod(n, 10)
    return [EN_TENS[tens * 10]] if unit == 0 else [f"{EN_TENS[tens * 10]}-{EN_UNITS[unit]}", f"{EN_TENS[tens * 10]} {EN_UNITS[unit]}"]


def _de(n: int) -> list[str]:
    if n < 20:
        return [DE_UNITS[n]] + (["ein", "eine"] if n == 1 else ["zwo"] if n == 2 else [])
    if n == 100:
        return ["hundert", "einhundert", "einhundert"]
    tens, unit = divmod(n, 10)
    if unit == 0:
        return [DE_TENS[tens * 10]]
    u = "ein" if unit == 1 else DE_UNITS[unit]
    return [f"{u}und{DE_TENS[tens * 10]}"]


def _fr(n: int) -> list[str]:
    if n < 20:
        return [FR_UNITS[n]]
    if n == 100:
        return ["cent"]
    if n < 70:
        tens, unit = divmod(n, 10)
        base = FR_TENS[tens * 10]
        if unit == 0:
            return [base]
        return [f"{base} et un", f"{base}-et-un"] if unit == 1 else [f"{base}-{FR_UNITS[unit]}", f"{base} {FR_UNITS[unit]}"]
    if n < 80:                                    # 70 to 79: soixante + 10 to 19
        r = n - 60
        base = "soixante"
        return [f"{base} et {FR_UNITS[r]}", f"{base}-et-{FR_UNITS[r]}"] if r == 11 else [f"{base}-{FR_UNITS[r]}", f"{base} {FR_UNITS[r]}"]
    r = n - 80                                    # 80 to 99: quatre-vingt + 0 to 19
    if r == 0:
        return ["quatre-vingts", "quatre-vingt", "quatre vingts"]
    return [f"quatre-vingt-{FR_UNITS[r]}", f"quatre vingt {FR_UNITS[r]}"]


def _es(n: int) -> list[str]:
    if n < 20:
        return [ES_UNITS[n]] + (["un", "una"] if n == 1 else [])
    if n < 30:
        return [ES_TWENTIES[n]] + (["veintiún", "veintiuna"] if n == 21 else [])
    if n == 100:
        return ["cien", "ciento"]
    tens, unit = divmod(n, 10)
    return [ES_TENS[tens * 10]] if unit == 0 else [f"{ES_TENS[tens * 10]} y {ES_UNITS[unit]}"]


_GEN = {"en": _en, "de": _de, "fr": _fr, "es": _es}
_ARTICLE_LIKE = {"one", "eins", "ein", "eine", "un", "una", "uno"}


@cache
def table(lang: str) -> dict[str, int]:
    """Folded number word -> value, for 2 to 100 (and zero), without the article-like forms of one."""
    out: dict[str, int] = {}
    for n in range(0, 101):
        if n == 1:
            continue
        for w in _GEN[lang](n):
            if w not in _ARTICLE_LIKE:
                out[fold(w)] = n
    return out


def phrases_longest_first(lang: str) -> list[str]:
    return sorted(table(lang), key=lambda w: (-len(w), w))
