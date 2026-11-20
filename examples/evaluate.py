"""Measure the verifier on the hand-written corpus in tests/corpus.py and print the numbers the README quotes.

    python examples/evaluate.py

Three measurements: false alarms on correct translations, how many deliberately broken translations are caught (by kind), and how often the
repair loop recovers when a backend makes one mistake and is told about it. Nothing here calls a model."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from babel_fish import FixtureBackend, Glossary, Profile, langid, protect, translate, verify  # noqa: E402
from tests.corpus import PAIRS, glossary_for  # noqa: E402

LANGS = ["de", "fr", "es"]


def glossary(p: dict, lang: str) -> Glossary | None:
    g = glossary_for(p, lang)
    return Glossary.from_dict(g) if g else None


def errors(src: str, out: str, lang: str, tone: str, spans: int, g: Glossary | None) -> list[str]:
    return [v.code for v in verify.check(src, out, source_lang="en", target_lang=lang, tone=tone, context="general", spans=spans, glossary=g) if v.severity == "error"]


def main() -> None:
    total = false_alarms = 0
    caught: dict[str, list[int]] = {}
    ident = ident_total = 0
    for p in PAIRS:
        spans = len(p.get("spans", []))
        for i, lang in enumerate(LANGS):
            good, g = p["formal"][lang], glossary(p, lang)
            total += 1
            false_alarms += bool(errors(p["src"], good, lang, "formal", spans, g))
            other_lang = LANGS[(i + 1) % 3]
            other = p["formal"][other_lang]
            ident_total += 1
            ident += langid.identify(good) == lang
            cases = {"left untranslated": (p["src"], "untranslated"), "translation refused": ("I'm sorry, I cannot translate this text.", "refusal"),
                     "preamble added": ("Here is the translation: " + good, "preamble"), "empty": ("  ", "empty"),
                     "wrong language": (other, "wrong_language")}
            m = None if spans else re.search(r"\d+", good)
            if m:
                cases["number changed"] = (good[:m.start()] + str(int(m.group()) + 1) + good[m.end():], "number_missing")
                cases["number dropped"] = (good[:m.start()] + good[m.end():], "number_missing")
            if spans:
                cases["placeholder lost"] = (good.replace(f"{protect.OPEN}1{protect.CLOSE}", "", 1), "placeholder")
            if "informal" in p:
                cases["wrong register"] = (p["informal"][lang], "register")
            if "wrong_term" in p:
                cases["wrong term"] = (p["wrong_term"][lang], "glossary")
            for name, (bad, code) in cases.items():
                hit = code in errors(p["src"], bad, lang, "formal", spans, g)
                caught.setdefault(name, [0, 0])
                caught[name][0] += hit
                caught[name][1] += 1
    print(f"clean translations flagged with an error: {false_alarms} of {total}")
    print(f"language identified correctly on the correct translations: {ident} of {ident_total}")
    print("broken translations caught:")
    for name, (h, n) in sorted(caught.items()):
        print(f"  {name:<18} {h:>3} of {n:<3}{'' if h == n else '   <- the misses are listed in the README'}")

    recovered = tries = 0
    for p in PAIRS:
        m = re.search(r"\d+", p["src"])
        if not m or p.get("spans"):
            continue
        for lang in LANGS:
            good = p["formal"][lang]
            gm = re.search(r"\d+", good)
            if not gm:
                continue
            first = good[:gm.start()] + str(int(gm.group()) + 1) + good[gm.end():]
            replies = iter([first, good])
            r = translate(p["src"], Profile(lang, "formal"), FixtureBackend(lambda s, u, it=replies: next(it)), glossary=glossary(p, lang))
            tries += 1
            recovered += r.ok and len(r.attempts) == 2
    print(f"one wrong number, repaired on the second attempt: {recovered} of {tries}")


if __name__ == "__main__":
    main()
