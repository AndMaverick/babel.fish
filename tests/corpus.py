"""A small parallel corpus written by hand: English sources with formal German, French and Spanish translations, informal variants for the sentences
that address the reader, and wrong-terminology variants. {"keep"} and {"terms"} are the glossary the pairs were written for.

⟦n⟧ tokens stand for protected spans exactly as the pipeline writes them;   is the French narrow no-break space in numbers."""
from __future__ import annotations

NB = " "
OPEN_, CLOSE_ = "⟦", "⟧"


def t(n: int) -> str:
    return f"{OPEN_}{n}{CLOSE_}"


# source, {lang: formal translation}, {lang: informal translation} (only where the sentence addresses the reader), {lang: wrong-term translation}
PAIRS: list[dict[str, object]] = [
    {"src": "Our product reduces costs by 20%.",
     "formal": {"de": "Unser Produkt senkt die Kosten um 20 %.", "fr": "Notre produit réduit les coûts de 20 %.", "es": "Nuestro producto reduce los costes en un 20 %."}},
    {"src": "Revenue grew from $1,200,000 in 2024 to $1,800,000 in 2025.",
     "formal": {"de": "Der Umsatz stieg von 1.200.000 $ im Jahr 2024 auf 1.800.000 $ im Jahr 2025.",
                "fr": f"Le chiffre d'affaires est passé de 1{NB}200{NB}000 $ en 2024 à 1{NB}800{NB}000 $ en 2025.",
                "es": "Los ingresos crecieron de 1.200.000 $ en 2024 a 1.800.000 $ en 2025."}},
    {"src": "Please send the signed contract by 20 November 2026.",
     "formal": {"de": "Bitte senden Sie den unterschriebenen Vertrag bis zum 20. November 2026 zurück.",
                "fr": "Veuillez nous renvoyer le contrat signé avant le 20 novembre 2026.",
                "es": "Le rogamos que nos envíe el contrato firmado antes del 20 de noviembre de 2026."},
     "informal": {"de": "Bitte sende uns deinen unterschriebenen Vertrag bis zum 20. November 2026 zurück.",
                  "fr": "Renvoie-nous ton contrat signé avant le 20 novembre 2026, s'il te plaît.",
                  "es": "Te rogamos que nos envíes tu contrato firmado antes del 20 de noviembre de 2026."}},
    {"src": f"Your account {t(1)} was created on 2026-03-15.", "spans": ["{name}"],
     "formal": {"de": f"Ihr Konto {t(1)} wurde am 15.03.2026 erstellt.", "fr": f"Votre compte {t(1)} a été créé le 15/03/2026.",
                "es": f"Su cuenta {t(1)} se creó el 15/03/2026."},
     "informal": {"de": f"Dein Konto {t(1)} wurde am 15.03.2026 erstellt.", "fr": f"Ton compte {t(1)} a été créé le 15/03/2026.",
                  "es": f"Tu cuenta {t(1)} se creó el 15/03/2026."}},
    {"src": "The meeting starts at 14:30 and lasts 90 minutes.",
     "formal": {"de": "Das Treffen beginnt um 14:30 Uhr und dauert 90 Minuten.", "fr": "La réunion commence à 14:30 et dure 90 minutes.",
                "es": "La reunión comienza a las 14:30 y dura 90 minutos."}},
    {"src": "We have 3 offices in 12 countries.",
     "formal": {"de": "Wir haben 3 Büros in 12 Ländern.", "fr": "Nous avons 3 bureaux dans 12 pays.", "es": "Tenemos 3 oficinas en 12 países."}},
    {"src": f"Thank you for your order. Visit {t(1)} for support.", "spans": ["https://example.com/help"],
     "formal": {"de": f"Vielen Dank für Ihre Bestellung. Besuchen Sie {t(1)}, wenn Sie Hilfe benötigen.",
                "fr": f"Merci pour votre commande. Consultez {t(1)} pour obtenir de l'aide.",
                "es": f"Gracias por su pedido. Visite {t(1)} para obtener ayuda."},
     "informal": {"de": f"Danke für deine Bestellung. Besuche {t(1)}, wenn du Hilfe brauchst.",
                  "fr": f"Merci pour ta commande. Consulte {t(1)} si tu as besoin d'aide.",
                  "es": f"Gracias por tu pedido. Visita {t(1)} si necesitas ayuda."}},
    {"src": "The cost of the license is 49.90 EUR per month.",
     "formal": {"de": "Die Kosten für die Lizenz betragen 49,90 EUR pro Monat.", "fr": "Le coût de la licence est de 49,90 EUR par mois.",
                "es": "El coste de la licencia es de 49,90 EUR al mes."}},
    {"src": "Interest is capped at 7.5% per year.",
     "formal": {"de": "Die Zinsen sind auf 7,5 % pro Jahr begrenzt.", "fr": "Les intérêts sont plafonnés à 7,5 % par an.",
                "es": "Los intereses están limitados al 7,5 % anual."}},
    {"src": "Twenty employees joined in the last quarter.",
     "formal": {"de": "Zwanzig Mitarbeitende sind im letzten Quartal beigetreten.",
                "fr": "Vingt employés ont rejoint l'entreprise au cours du dernier trimestre.",
                "es": "Veinte empleados se incorporaron en el último trimestre."}},
    {"src": "Please contact us if you have any questions about your invoice.",
     "formal": {"de": "Bitte kontaktieren Sie uns, wenn Sie Fragen zu Ihrer Rechnung haben.",
                "fr": "Veuillez nous contacter si vous avez des questions concernant votre facture.",
                "es": "Póngase en contacto con nosotros si tiene preguntas sobre su factura."},
     "informal": {"de": "Bitte kontaktiere uns, wenn du Fragen zu deiner Rechnung hast.",
                  "fr": "Contacte-nous si tu as des questions sur ta facture.",
                  "es": "Contáctanos si tienes preguntas sobre tu factura."}},
    {"src": "The board approved the budget of 2.5 million dollars.",
     "formal": {"de": "Der Vorstand hat das Budget von 2,5 Millionen Dollar genehmigt.", "fr": "Le conseil a approuvé le budget de 2,5 millions de dollars.",
                "es": "La junta aprobó el presupuesto de 2,5 millones de dólares."}},
    {"src": "Delivery takes 3 to 5 business days.",
     "formal": {"de": "Die Lieferung dauert 3 bis 5 Werktage.", "fr": "La livraison prend 3 à 5 jours ouvrables.", "es": "La entrega tarda de 3 a 5 días hábiles."}},
    {"src": "Acme Cloud keeps your data secure and encrypted.", "glossary": {"terms": {"data": {"de": "Daten", "fr": "données", "es": "datos"}}, "keep": ["Acme Cloud"]},
     "formal": {"de": "Acme Cloud schützt Ihre Daten und hält sie verschlüsselt.", "fr": "Acme Cloud protège vos données et les garde chiffrées.",
                "es": "Acme Cloud protege sus datos y los mantiene cifrados."},
     "informal": {"de": "Acme Cloud schützt deine Daten und hält sie verschlüsselt.", "fr": "Acme Cloud protège tes données et les garde chiffrées.",
                  "es": "Acme Cloud protege tus datos y los mantiene cifrados."},
     "wrong_term": {"de": "Acme Cloud schützt Ihre Informationen und hält sie verschlüsselt.", "fr": "Acme Cloud protège vos informations et les garde chiffrées.",
                    "es": "Acme Cloud protege su información y la mantiene cifrada."}},
    {"src": "Our team of 45 engineers works in 3 time zones.",
     "formal": {"de": "Unser Team aus 45 Ingenieuren arbeitet in 3 Zeitzonen.", "fr": "Notre équipe de 45 ingénieurs travaille dans 3 fuseaux horaires.",
                "es": "Nuestro equipo de 45 ingenieros trabaja en 3 husos horarios."}},
    {"src": "The warranty covers repairs for 24 months from the date of purchase.",
     "formal": {"de": "Die Garantie deckt Reparaturen für 24 Monate ab Kaufdatum ab.",
                "fr": "La garantie couvre les réparations pendant 24 mois à compter de la date d'achat.",
                "es": "La garantía cubre las reparaciones durante 24 meses desde la fecha de compra."}},
    {"src": "We expect revenue of $4.2 million in the first quarter of 2027.",
     "formal": {"de": "Wir erwarten im ersten Quartal 2027 einen Umsatz von 4,2 Millionen $.",
                "fr": "Nous prévoyons un chiffre d'affaires de 4,2 millions de $ au premier trimestre 2027.",
                "es": "Esperamos unos ingresos de 4,2 millones de $ en el primer trimestre de 2027."}},
    {"src": f"Click {t(1)}Save{t(2)} to keep your changes, or press {t(3)} to cancel.", "spans": ["<b>", "</b>", "%s"],
     "formal": {"de": f"Klicken Sie auf {t(1)}Speichern{t(2)}, um Ihre Änderungen zu behalten, oder drücken Sie {t(3)}, um abzubrechen.",
                "fr": f"Cliquez sur {t(1)}Enregistrer{t(2)} pour conserver vos modifications, ou appuyez sur {t(3)} pour annuler.",
                "es": f"Haga clic en {t(1)}Guardar{t(2)} para conservar sus cambios, o pulse {t(3)} para cancelar."},
     "informal": {"de": f"Klicke auf {t(1)}Speichern{t(2)}, um deine Änderungen zu behalten, oder drücke {t(3)}, um abzubrechen.",
                  "fr": f"Clique sur {t(1)}Enregistrer{t(2)} pour garder tes modifications, ou appuie sur {t(3)} pour annuler.",
                  "es": f"Haz clic en {t(1)}Guardar{t(2)} para conservar tus cambios, o pulsa {t(3)} para cancelar."}},
    {"src": "This agreement is valid until 31 December 2027.",
     "formal": {"de": "Diese Vereinbarung gilt bis zum 31. Dezember 2027.", "fr": "Le présent accord est valable jusqu'au 31 décembre 2027.",
                "es": "El presente acuerdo es válido hasta el 31 de diciembre de 2027."}},
    {"src": "Two of the five directors voted against the proposal.",
     "formal": {"de": "Zwei der fünf Direktoren haben gegen den Vorschlag gestimmt.", "fr": "Deux des cinq administrateurs ont voté contre la proposition.",
                "es": "Dos de los cinco directores votaron en contra de la propuesta."}},
]
LANGS = ("de", "fr", "es")


def glossary_for(pair: dict[str, object], lang: str) -> dict[str, object] | None:
    g = pair.get("glossary")
    if not g:
        return None
    return {"terms": {k: v[lang] for k, v in g["terms"].items()}, "keep": g["keep"]}      # type: ignore[index,attr-defined]
