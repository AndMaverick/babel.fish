"""Which of English, German, French and Spanish a text is written in, from stop words. Short texts are reported as unknown, not guessed."""
from __future__ import annotations

import re

from .text import folded_tokens, tokens

STOP = {
    "en": ["the", "and", "of", "to", "in", "is", "that", "it", "for", "as", "with", "was", "on", "be", "by", "this", "are", "from", "or", "an", "at", "not", "you", "we", "they", "have", "has", "had", "but", "his", "her", "their", "which", "will", "would", "can", "all", "our", "your", "been", "were", "its", "than", "then", "there", "these", "those", "when", "what", "who", "into", "over", "also", "more", "most", "such", "only", "other"],
    "de": ["der", "die", "das", "und", "ist", "nicht", "ein", "eine", "zu", "den", "dem", "mit", "auf", "fur", "von", "sie", "es", "im", "sich", "auch", "an", "als", "bei", "oder", "nach", "wie", "aber", "aus", "wir", "sehr", "wird", "werden", "sind", "wurde", "haben", "hat", "kann", "ihre", "ihr", "ihnen", "unser", "unsere", "dass", "noch", "nur", "einen", "einer", "eines", "des", "zum", "zur", "um", "uber", "unter", "bis", "durch", "gegen", "ohne", "wenn"],
    "fr": ["le", "la", "les", "des", "du", "une", "et", "est", "qui", "dans", "pour", "pas", "sur", "avec", "au", "aux", "ce", "cette", "ces", "nous", "vous", "il", "elle", "ils", "sont", "ete", "ne", "plus", "par", "ou", "mais", "son", "sa", "ses", "leur", "notre", "votre", "ont", "etre", "fait", "comme", "tout", "tous", "aussi", "entre", "sans", "sous", "apres", "avant", "chez", "si", "lors"],
    "es": ["el", "los", "las", "del", "una", "y", "es", "por", "con", "para", "no", "se", "su", "sus", "al", "lo", "como", "mas", "pero", "este", "esta", "estos", "son", "nuestro", "nuestra", "usted", "ustedes", "ha", "han", "ser", "fue", "desde", "hasta", "durante", "muy", "tambien", "sobre", "entre", "cuando", "todo", "esa", "ese", "le", "les", "ya", "sin", "sus", "tiene", "tienen", "hay", "donde"],
}
MIN_TOKENS = 4
MIN_HITS = 2
MARGIN = 1.3


_CHARS = {"fr": re.compile("[àèùâêîôûëïçœ]"), "es": re.compile("[áíóúñ¿¡]"), "de": re.compile("[äöüß]")}
_ELISION = re.compile(r"^(?:[ldjnscm]|qu|jusqu|lorsqu)['\u2019]\w", re.IGNORECASE)


def scores(text: str) -> dict[str, int]:
    """Stop word hits per language, plus one for each word with letters that only that language uses (ñ, ç, ä ...) and for French elisions (l', d')."""
    toks = folded_tokens(text)
    out = {lang: sum(t in set(words) for t in toks) for lang, words in STOP.items()}
    for raw in tokens(text):
        low = raw.lower()
        for lang, rx in _CHARS.items():
            if rx.search(low):
                out[lang] += 1
        if _ELISION.match(low):
            out["fr"] += 1
    return out


def identify(text: str) -> str:
    """'en', 'de', 'fr', 'es' or 'unknown'. Needs at least 4 words, 2 stop words of the winner and a 30% margin over the runner-up."""
    if len(folded_tokens(text)) < MIN_TOKENS:
        return "unknown"
    ranked = sorted(scores(text).items(), key=lambda kv: (-kv[1], kv[0]))
    (best, hits), (_, second) = ranked[0], ranked[1]
    if hits >= MIN_HITS and hits >= MARGIN * second:
        return best
    return "unknown"
