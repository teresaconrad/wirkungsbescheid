"""Extraktions-Prompt: Bescheid-Bilder → kanonisches JSON-Schema."""
from __future__ import annotations

import json

from ..models import Bescheid

SYSTEM = """Du extrahierst Daten aus deutschen Einkommensteuerbescheiden in ein festes JSON-Schema.

Regeln:
1. Extrahiere NUR, was im Dokument steht. Rate nie. Fehlende Felder: null/weglassen.
2. DATENSCHUTZ: Steuer-ID, IdNr., IBAN, Namen, Adressen werden NIEMALS ausgegeben —
   sie sind nicht Teil des Schemas. Das Feld meta.anrede bleibt IMMER null,
   auch wenn ein Name im Dokument steht.
3. Beträge als Zahl (Punkt als Dezimaltrenner): "1.234,56 EUR" → 1234.56.
4. Negative Vorzeichen und "ab"-Zeilen beachten: Abzüge als positive Beträge im
   jeweiligen Abzugsfeld.
5. Bei Zusammenveranlagung: Spalten sauber Person A (links) / Person B (rechts) zuordnen.
6. "dazu Anspruch auf Kindergeld" → festsetzung.hinzurechnung_kindergeld.
7. Lohn-/Entgeltersatzleistungen (§ 32b, Progressionsvorbehalt) → lohnersatzleistungen
   der richtigen Person; nach DBA steuerfreie Einkünfte → auslaendische_einkuenfte_dba.
8. Besonderer Steuersatz (Prozent, 4 Nachkommastellen) → festsetzung.steuersatz_besonders.
9. Vorläufigkeitsvermerke (§ 165 AO): Stichpunkte in meta.vorlaeufigkeitsvermerke.
10. Für jedes unsichere Feld: provenienz.konfidenz < 1.0 setzen, seite angeben.
11. Antworte AUSSCHLIESSLICH mit dem JSON-Objekt, ohne Markdown-Zaun, ohne Kommentar.
"""


def user_prompt(textlayer: str | None = None, korrekturhinweis: str | None = None) -> str:
    teile = ["Extrahiere den Bescheid in das folgende JSON-Schema:\n",
             json.dumps(Bescheid.model_json_schema(), ensure_ascii=False)]
    if textlayer:
        teile.append("\n\nZusätzlich der maschinelle Textlayer des PDFs (kann Layoutfehler "
                     "enthalten, Bilder sind maßgeblich):\n" + textlayer[:20000])
    if korrekturhinweis:
        teile.append("\n\nKORREKTUR ERFORDERLICH — die Nachrechnung ergab Abweichungen:\n"
                     + korrekturhinweis
                     + "\nPrüfe die betroffenen Felder erneut Ziffer für Ziffer.")
    return "".join(teile)
