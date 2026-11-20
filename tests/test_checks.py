import random
import unittest
from decimal import Decimal

from babel_fish import Glossary, langid, protect, verify
from babel_fish import numbers as nums
from babel_fish.numwords import table
from babel_fish.register import check as register_check
from babel_fish.text import fold
from tests.corpus import LANGS, PAIRS, glossary_for


def vals(text, lang):
    return dict(nums.extract(text, lang))


class TestNumberWords(unittest.TestCase):
    CASES = {
        "en": {"two": 2, "twenty": 20, "twenty-one": 21, "twenty one": 21, "ninety-nine": 99, "fourteen": 14, "one hundred": 100},
        "de": {"zwei": 2, "zwölf": 12, "einundzwanzig": 21, "neunundneunzig": 99, "dreißig": 30, "dreissig": 30, "siebzig": 70, "hundert": 100, "null": 0},
        "fr": {"deux": 2, "dix-sept": 17, "vingt et un": 21, "vingt-deux": 22, "trente et un": 31, "soixante-dix": 70, "soixante et onze": 71, "soixante-douze": 72,
               "quatre-vingts": 80, "quatre-vingt-un": 81, "quatre-vingt-dix": 90, "quatre-vingt-onze": 91, "quatre-vingt-dix-neuf": 99, "cent": 100},
        "es": {"dos": 2, "dieciséis": 16, "veinte": 20, "veintiuno": 21, "veintidós": 22, "treinta": 30, "treinta y uno": 31, "cuarenta y cinco": 45, "noventa y nueve": 99,
               "cien": 100},
    }

    def test_hand_written_cases(self):
        for lang, cases in self.CASES.items():
            t = table(lang)
            for word, n in cases.items():
                self.assertEqual(t[fold(word)], n, (lang, word))

    def test_articles_are_not_numbers(self):
        for lang, w in (("en", "one"), ("de", "ein"), ("de", "eine"), ("fr", "un"), ("es", "uno"), ("es", "una")):
            self.assertNotIn(w, table(lang))

    def test_every_value_from_2_to_100_has_a_word(self):
        for lang in ("en", "de", "fr", "es"):
            self.assertEqual({n for n in table(lang).values() if n >= 2} | {1}, set(range(1, 101)) | set(), lang)


class TestNumbers(unittest.TestCase):
    def test_conventions(self):
        self.assertEqual(vals("1,234.56", "en"), {Decimal("1234.56"): 1})
        self.assertEqual(vals("1.234,56", "de"), {Decimal("1234.56"): 1})
        self.assertEqual(vals("1.234,56", "es"), {Decimal("1234.56"): 1})
        for sep in (" ", " ", " "):
            self.assertEqual(vals(f"1{sep}234,56", "fr"), {Decimal("1234.56"): 1})

    def test_same_digits_different_value_by_language(self):
        self.assertEqual(vals("1.234", "en"), {Decimal("1.234"): 1})
        self.assertEqual(vals("1.234", "de"), {Decimal("1234"): 1})
        self.assertEqual(vals("1,5", "en"), {Decimal(1): 1, Decimal(5): 1})
        self.assertEqual(vals("1,5", "de"), {Decimal("1.5"): 1})

    def test_percent_currency_and_words_are_ignored_or_equal(self):
        self.assertEqual(vals("20%", "en"), vals("20 %", "de"))
        self.assertEqual(vals("20 percent", "en"), vals("zwanzig Prozent", "de"))
        self.assertEqual(vals("$1,200,000", "en"), vals("1.200.000 $", "de"))
        self.assertEqual(vals("twenty-one days", "en"), {Decimal(21): 1})

    def test_dates_and_times_agree_across_formats(self):
        a = vals("by 2026-11-20 at 14:30", "en")
        b = vals("bis 20.11.2026 um 14:30 Uhr", "de")
        self.assertEqual(a, b)
        self.assertEqual(vals("11/20/2026", "en"), vals("20.11.2026", "de"))

    def test_protected_tokens_carry_no_numbers(self):
        self.assertEqual(vals(f"see {protect.OPEN}12{protect.CLOSE} now", "en"), {})

    def test_compare(self):
        m, a = nums.compare(nums.extract("20% and 3 offices", "en"), nums.extract("25 % und 3 Büros", "de"))
        self.assertEqual(([nums.show(x) for x in m], [nums.show(x) for x in a]), (["20"], ["25"]))

    def test_every_value_in_the_corpus_survives_a_roundtrip(self):
        for p in PAIRS:
            src = nums.extract(protect.TOKEN.sub(" ", p["src"]), "en")
            for lang in LANGS:
                missing, added = nums.compare(src, nums.extract(protect.TOKEN.sub(" ", p["formal"][lang]), lang))
                self.assertEqual((missing, added), ([], []), (p["src"], lang))


class TestProtect(unittest.TestCase):
    def test_roundtrip_property(self):
        frags = ["Hello {name}", " ", "%s", "%(count)d", "<b>", "</b>", "https://x.org/a?b=1", "a@b.com", "`code`", "{{tpl}}", "${HOME}", "plain", ".", "20%", "\n"]
        rng = random.Random(1)
        for _ in range(500):
            text = "".join(rng.choice(frags) for _ in range(rng.randint(1, 12)))
            m = protect.mask(text)
            self.assertEqual(protect.unmask(m.text, m.spans), text)
            self.assertEqual(protect.token_problems(m.text, len(m.spans)), ([], [], []))

    def test_what_is_protected(self):
        m = protect.mask("Click <b>Save</b> at https://a.org/x or mail me@x.io; use {user} and %s, `rm -rf`, {{x}}.")
        self.assertEqual(m.spans, ("<b>", "</b>", "https://a.org/x", "me@x.io", "{user}", "%s", "`rm -rf`", "{{x}}"))

    def test_a_percent_sign_in_prose_is_not_a_placeholder(self):
        self.assertEqual(protect.mask("20 %sehr gut and 5 % off").spans, ())

    def test_problems(self):
        self.assertEqual(protect.token_problems("a ⟦1⟧ b", 2), (["⟦2⟧"], [], []))
        self.assertEqual(protect.token_problems("⟦1⟧ ⟦1⟧", 1), ([], ["⟦1⟧"], []))
        self.assertEqual(protect.token_problems("⟦1⟧ ⟦9⟧", 1), ([], [], ["⟦9⟧"]))


class TestLangid(unittest.TestCase):
    def test_clear_cases(self):
        self.assertEqual(langid.identify("The team has built this product for all of our customers."), "en")
        self.assertEqual(langid.identify("Das Team hat dieses Produkt für alle unsere Kunden gebaut und ist sehr zufrieden."), "de")
        self.assertEqual(langid.identify("Le produit est dans les mains de nos clients et ils sont très contents de la qualité."), "fr")
        self.assertEqual(langid.identify("El producto está en las manos de nuestros clientes y están muy contentos con la calidad."), "es")

    def test_short_text_is_unknown_not_guessed(self):
        self.assertEqual(langid.identify("Hello world"), "unknown")
        self.assertEqual(langid.identify(""), "unknown")


class TestRegister(unittest.TestCase):
    def codes(self, text, lang, tone, ctx="general"):
        return [(v.code, v.severity) for v in register_check(text, lang, tone, ctx)]

    def test_german(self):
        self.assertTrue(self.codes("Bitte sende uns deinen Vertrag.", "de", "formal"))
        self.assertFalse(self.codes("Bitte senden Sie uns Ihren Vertrag.", "de", "formal"))
        self.assertTrue(self.codes("Hast du Fragen zu Ihrer Rechnung?", "de", "casual"))
        self.assertFalse(self.codes("Sie hat gesagt, sie komme morgen.", "de", "casual"))           # lowercase sie, and Sie at a sentence start
        self.assertFalse(self.codes("Sie sind willkommen.", "de", "casual"))

    def test_french_and_spanish(self):
        self.assertTrue(self.codes("Contacte-nous si tu as des questions.", "fr", "formal"))
        self.assertFalse(self.codes("Contactez-nous si vous avez des questions.", "fr", "formal"))
        self.assertEqual(self.codes("Contactez-nous si vous avez des questions.", "fr", "casual"), [("register", "warning")])
        self.assertTrue(self.codes("Tu cuenta fue creada.", "es", "formal"))
        self.assertFalse(self.codes("Su cuenta fue creada. Té verde.", "es", "formal"))

    def test_english(self):
        self.assertTrue(self.codes("We don't expect delays.", "en", "formal"))
        self.assertTrue(self.codes("We don't expect delays.", "en", "casual", "legal"))
        self.assertFalse(self.codes("We don't expect delays.", "en", "casual"))
        self.assertEqual(self.codes("Hey, this is awesome.", "en", "formal"), [("register", "warning")])


class TestGlossary(unittest.TestCase):
    def test_terms_and_keep(self):
        g = Glossary.from_dict({"terms": {"data": "Daten"}, "keep": ["Acme Cloud"]})
        self.assertEqual(verify.gloss.check("Acme Cloud keeps your data safe.", "Acme Cloud schützt Ihre Daten.", g), [])
        codes = [v.code for v in verify.gloss.check("Acme Cloud keeps your data safe.", "Acme Wolke schützt Ihre Informationen.", g)]
        self.assertEqual(sorted(codes), ["glossary", "keep"])

    def test_term_only_required_when_the_source_has_it(self):
        g = Glossary.from_dict({"terms": {"data": "Daten"}})
        self.assertEqual(verify.gloss.check("Hello there.", "Hallo.", g), [])
        self.assertEqual(verify.gloss.check("The database is fast.", "Die Datenbank ist schnell.", g), [])   # "database" is not "data"

    def test_bad_glossaries(self):
        from babel_fish import BabelError
        for bad in ([], {"terms": []}, {"terms": {"a": 1}}, {"keep": "x"}, {"other": 1}, {"terms": {"": "x"}}):
            with self.assertRaises(BabelError):
                Glossary.from_dict(bad)


class TestVerifierOnTheCorpus(unittest.TestCase):
    def check(self, src, out, lang, tone="formal", ctx="general", spans=0, g=None):
        return verify.check(src, out, source_lang="en", target_lang=lang, tone=tone, context=ctx, spans=spans, glossary=Glossary.from_dict(g) if g else None)

    def errors(self, *a, **k):
        return [v.code for v in self.check(*a, **k) if v.severity == "error"]

    def test_clean_translations_have_no_errors(self):
        for p in PAIRS:
            for lang in LANGS:
                got = self.errors(p["src"], p["formal"][lang], lang, spans=len(p.get("spans", [])), g=glossary_for(p, lang))
                self.assertEqual(got, [], (p["src"], lang))

    def test_every_corruption_is_caught(self):
        import re
        for p in PAIRS:
            spans = len(p.get("spans", []))
            for i, lang in enumerate(LANGS):
                good, g = p["formal"][lang], glossary_for(p, lang)
                other = p["formal"][LANGS[(i + 1) % 3]]
                tests = {"untranslated": (p["src"], "untranslated"),
                         "refusal": ("I'm sorry, I cannot translate this text.", "refusal"), "preamble": ("Here is the translation: " + good, "preamble"),
                         "empty": ("  ", "empty")}
                if langid.identify(other) == LANGS[(i + 1) % 3]:          # a very short sentence may not be identifiable; the figure is in the README
                    tests["wrong_language"] = (other, "wrong_language")
                m = re.search(r"\d+", good.replace(protect.OPEN, "\0").replace(protect.CLOSE, "\0")) if not spans else None
                if m:
                    tests["number_changed"] = (good[:m.start()] + str(int(m.group()) + 1) + good[m.end():], "number_missing")
                    tests["number_dropped"] = (good[:m.start()] + good[m.end():], "number_missing")
                if spans:
                    tests["placeholder"] = (good.replace(f"{protect.OPEN}1{protect.CLOSE}", "", 1), "placeholder")
                if "informal" in p:
                    tests["informal"] = (p["informal"][lang], "register")
                if "wrong_term" in p:
                    tests["term"] = (p["wrong_term"][lang], "glossary")
                for name, (bad, code) in tests.items():
                    self.assertIn(code, self.errors(p["src"], bad, lang, spans=spans, g=g), (name, lang, p["src"]))


if __name__ == "__main__":
    unittest.main()
