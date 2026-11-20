"""The verifier: everything about a translation that can be checked without a second opinion from a model.

It cannot say a translation is good. It can say a translation is wrong in one of the ways that matter most to a reader who does not
speak the target language: a number changed, a placeholder lost, the text left untranslated or in the wrong language, the wrong
form of address, a required term missing, a reply that is an apology or a preamble instead of a translation."""
from __future__ import annotations

from . import glossary as gloss
from . import langid, protect, register
from . import numbers as nums
from .text import fold, tokens
from .violations import Violation

REFUSALS = ("i'm sorry", "i am sorry", "i cannot", "i can't", "as an ai", "es tut mir leid", "ich kann nicht", "je suis desole", "je ne peux pas",
            "lo siento", "no puedo")
PREAMBLES = ("here is the translation", "here's the translation", "translation:", "hier ist die ubersetzung", "ubersetzung:", "voici la traduction",
             "traduction :", "aqui esta la traduccion", "traduccion:", "sure,", "certainly")
MIN_RATIO, MAX_RATIO = 0.4, 2.5


def check(source: str, output: str, *, source_lang: str, target_lang: str, tone: str, context: str, spans: int = 0,
          glossary: gloss.Glossary | None = None) -> list[Violation]:
    """``source`` and ``output`` are the masked texts (placeholders as numbered tokens); ``spans`` is how many tokens the source holds."""
    out: list[Violation] = []
    if not output.strip():
        return [Violation("empty", "error", "the reply is empty")]
    head = fold(output.strip())[:60]
    if any(head.startswith(fold(r)) for r in REFUSALS):
        out.append(Violation("refusal", "error", "the reply is a refusal or an apology, not a translation"))
    if any(head.startswith(fold(p)) for p in PREAMBLES):
        out.append(Violation("preamble", "error", "the reply starts with a preamble instead of the translation"))

    missing, repeated, unknown = protect.token_problems(output, spans)
    if missing:
        out.append(Violation("placeholder", "error", f"protected text lost: {' '.join(missing)}"))
    if repeated:
        out.append(Violation("placeholder", "error", f"protected text repeated: {' '.join(repeated)}"))
    if unknown:
        out.append(Violation("placeholder", "error", f"protected text invented: {' '.join(unknown)}"))

    plain_src = protect.TOKEN.sub(" ", source)
    plain_out = protect.TOKEN.sub(" ", output)
    has_letters = any(c.isalpha() for c in plain_src)
    if has_letters and source_lang != target_lang and fold(plain_src).split() == fold(plain_out).split():
        out.append(Violation("untranslated", "error", "the output is the source text, unchanged"))

    if has_letters:
        got = langid.identify(plain_out)
        if got not in (target_lang, "unknown") and source_lang != target_lang:
            out.append(Violation("wrong_language", "error", f"the output reads as {got}, not {target_lang}"))
        elif got == "unknown" and len(tokens(plain_out)) >= 8:
            out.append(Violation("language_unverified", "warning", f"could not confirm that the output is {target_lang}"))

    sv = nums.extract(plain_src, source_lang)
    ov = nums.extract(plain_out, target_lang)
    missing_n, added_n = nums.compare(sv, ov)
    if missing_n:
        out.append(Violation("number_missing", "error", "numbers in the source that the output lacks or changed: " + ", ".join(map(nums.show, missing_n))))
    if added_n:
        out.append(Violation("number_added", "warning", "numbers in the output that the source does not have: " + ", ".join(map(nums.show, added_n))))

    if glossary:
        out += gloss.check(plain_src, plain_out, glossary)
    out += register.check(plain_out, target_lang, tone, context)

    ws, wo = len(tokens(plain_src)), len(tokens(plain_out))
    if ws >= 6 and not MIN_RATIO <= wo / ws <= MAX_RATIO:
        out.append(Violation("length", "warning", f"the output has {wo} words for {ws} in the source"))
    return out
