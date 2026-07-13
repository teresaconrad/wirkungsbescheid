# Wirkungsbescheid — Prototyp-Blueprint (Upload → Extraktion → Kombi-Bescheid)

**Stand:** Juli 2026 · **Basis:** 00–10, insb. Datenmodell (03), Realfall-Durchspiel (09), Mock Fall K (10)
**Ziel:** Voll funktionsfähiger Demonstrator: echter Steuerbescheid rein (PDF/JPEG/PNG/HEIC), kombinierter Steuer- und Wirkungsbescheid raus — fallabhängig gerendert (P16), mit allen steuerlichen Besonderheiten.

---

## 1. Architektur: Sieben Stufen

```
UPLOAD ► [1] Vorverarbeitung ► [2] Extraktion ► [3] Validierung/Nachrechnung
                                                        │
AUSGABE ◄ [7] Rendering ◄ [6] Wirkungsmodell ◄ [5] Effekt-Rechner ◄ [4] Fall-Erkennung
```

**[1] Vorverarbeitung.** HEIC→PNG-Konvertierung, Mehrseiten-Handling, Foto-Aufbereitung (Ausrichtung, Kontrast). Born-digital-PDFs zusätzlich per Textlayer-Extraktion (schneller, fehlerfreier als OCR).

**[2] Extraktion.** LLM-Vision (Claude API) liest den Bescheid gegen ein festes **JSON-Schema** aus — nicht Freitext-OCR + Regex. Grund: Bescheid-Layouts variieren je Bundesland/Jahr/ELSTER-Version, Fotos sind schief, und Felder wie „Hinzurechnung Kindergeld" brauchen semantisches Verständnis. Jedes Feld bekommt Konfidenz + Fundstelle (Seite).

**[3] Validierung durch Nachrechnung — das Herzstück der Qualitätssicherung.** Eine deterministische **Steuer-Engine** (Python) rechnet aus den extrahierten Eingangsgrößen die festgesetzte Steuer nach. Stimmt sie auf den Euro mit dem extrahierten Wert überein, ist die Extraktion praktisch sicher korrekt. Weicht sie ab: gezielter Zweitversuch bzw. Korrektur-Screen für die Nutzer:in. Kein anderes QA-Verfahren ist so stark — und es ist genau die „Keine neuen Daten nötig"-Logik, nur umgekehrt angewandt.

**[4] Fall-Erkennung.** Aus dem Schema werden die Fallmerkmale abgeleitet (Matrix in Abschnitt 3) und die konditionalen Bausteine aktiviert: welche „Was heißt das?"-Boxen, welche Seiten-Module, Erstattungs- vs. Nachzahlungspfad.

**[5] Effekt-Rechner („Ihr Jahr in 5 Zahlen").** Die Engine rechnet die Kontrafaktuale, die das Finanzamt intern ohnehin rechnet: Splitting-Vorteil (Differenz zu zwei Einzelveranlagungen), Progressionsvorbehalts-Effekt, Kindervorteil aus der Günstigerprüfung, Soli-Ersparnis in der Milderungszone. Exakt nach amtlichen Rundungsregeln (§ 32a Abs. 5/6 EStG), nicht überschlägig wie in Doku 09.

**[6] Wirkungsmodell.** Pipeline aus Doku 03 unverändert: Ebenen-Split (Art. 106 GG, Stadtstaaten-Sonderfall), COFOG-Kategorienmix je Ebene, Zins-Split, Einheiten-Übersetzung, Kreislauf-Modul (eingezahlt vs. zurückgeflossen — Kindergeld steht ja im Bescheid), Delta-Kasten. Alle Daten als **versioniertes Datenpaket** (JSON mit Quelle + Preisstand je Wert), getrennt vom Code — jährlich austauschbar.

**[7] Rendering.** Das Fall-K-Mock (10) wird von Hand-HTML zu einem **Jinja2-Template mit konditionalen Bausteinen** generalisiert. Ausgabe: Web-Ansicht + PDF über die bestehende Playwright-Pipeline (`make_flow_pdf.py`, uniform 0.644). Dazwischen ein **Review-Screen**: extrahierte Werte mit Konfidenz-Markierung, korrigierbar — wichtig für Vertrauen und für Fotos mit schlechter Qualität.

**Technik-Stack (Vorschlag):** Python + FastAPI (Web-Shell, Upload), Claude API mit Structured Output (Extraktion), eigene Tarif-Bibliothek (Engine), Jinja2 + Playwright (Rendering). Alles außer der Extraktion läuft deterministisch und offline.

---

## 2. Das kanonische Bescheid-Schema (Voraussetzung Nr. 1)

Der Vertrag zwischen allen Stufen. Grobstruktur:

| Block | Inhalt |
|---|---|
| Meta | Finanzamt, Steuernummer (maskiert), Bescheiddatum, Veranlagungsjahr, Bescheidart (Erst/Änderung), Vorläufigkeitsvermerke |
| Veranlagung | Einzel/Zusammen, Bundesland, Kirchensteuer ja/nein, Kinder (Anzahl, Freibeträge) |
| Einkünfte je Person | Bruttolohn, Werbungskosten, Kapital (tariflich/abgeltend), V+V, selbständig/gewerblich, Renten, sonstige |
| Abzüge | Vorsorge, Sonderausgaben, Spenden, Kinderbetreuung, agB (geltend gemacht + zumutbare Belastung + abziehbar), Ausbildungsfreibetrag, § 35a |
| Progression | steuerfreie Lohnersatzleistungen je Person (Elterngeld, Kurzarbeit, ALG…), besonderer Steuersatz |
| Festsetzung | zvE, Tarif, tarifliche ESt, Hinzurechnung Kindergeld, Ermäßigungen (§ 35a…), festgesetzte ESt, Soli, KiSt |
| Abrechnung | Abzugsteuern (LSt, KapESt), Vorauszahlungen geleistet, Erstattung/Nachzahlung, künftige Vorauszahlungen |
| Provenienz | je Feld: Konfidenz, Seite, extrahiert vs. berechnet vs. nutzerkorrigiert |

---

## 3. Fallkonstellations-Matrix (Voraussetzung Nr. 2)

Definiert, was der Prototyp *kann* — und was er ehrlich als „noch nicht abgedeckt" kennzeichnet (P9/P15: Lücken ausweisen statt kaschieren).

**v1 — Pflicht (deckt geschätzt >90 % der Arbeitnehmer:innen-Bescheide):**

| Dimension | Ausprägungen |
|---|---|
| Veranlagung | Einzel · Zusammen/Splitting |
| Ergebnis | Erstattung · Nachzahlung · Null |
| Kinder | ohne · mit (inkl. Günstigerprüfung Kindergeld/Freibeträge, beide Ausgänge) |
| Progressionsvorbehalt | ohne · mit (Elterngeld, Kurzarbeit, ALG I, Krankengeld) |
| Soli | null · Milderungszone · voll |
| Kapitalerträge | keine · abgeltend · tariflich (§ 32d Abs. 6) |
| Weitere Einkünfte | V+V · Renten (Besteuerungsanteil) |
| Abzüge | zumutbare Belastung · § 35a haushaltsnah/Handwerker · Spenden · Kinderbetreuung |
| Sonstiges | Vorläufigkeit § 165 AO · Vorauszahlungen · Kirchensteuer (Ausweis, ohne Wirkungsmodell) · Lohnersatz-Zuschüsse |

**v2 — dokumentierte Ausbaustufe:** selbständige/gewerbliche Einkünfte, Verlustvor-/-rücktrag, ausländische Einkünfte/DBA-Progressionsvorbehalt, Faktorverfahren-Erklärzeile, Änderungs-/Einspruchsbescheide, Unterhalt/Realsplitting.

**Degradations-Regel:** Erkennt Stufe 4 ein v2-Merkmal, rendert der Prototyp trotzdem — mit gekennzeichnetem Baustein „Diesen Punkt erklärt der Demonstrator noch nicht". Kein stiller Fehler.

---

## 4. Steuer-Engine: Umfang v1

Exakt zu implementieren (jeweils mit amtlichen Rundungsregeln, Referenz: BMF-Steuerrechner):
§ 32a Tarif (Jahre 2023–2025, Grund + Splitting) · § 32b Progressionsvorbehalt (besonderer Steuersatz) · § 31/§ 66 Günstigerprüfung inkl. Kindergeld-Hinzurechnung · SolZG mit Freigrenze + Milderungszone · § 33 Abs. 3 zumutbare Belastung (stufenweise Berechnung, BFH-konform) · § 32d Abs. 6 Günstigerprüfung Kapital · § 35a Ermäßigungen · Vorsorgeaufwendungen-Höchstbeträge (vereinfacht, da Eingangswerte aus dem Bescheid extrahiert werden).

**Testverfahren:** Unit-Tests gegen BMF-Steuerrechner-Referenzwerte + Fall K als Golden Case (alle Zwischensummen aus Doku 09 müssen auf den Euro reproduziert werden).

---

## 5. Was fehlt noch — und wie wir es herstellen

| # | Voraussetzung | Weg | Aufwand |
|---|---|---|---|
| 1 | **Bescheid-Schema** (Abschn. 2) finalisieren | aus Fall K + Mustermann-Mock ableiten; ich erstelle Entwurf | 1 Session |
| 2 | **Fallmatrix** v1/v2 festziehen | Abschn. 3 als Entscheidungsvorlage; deine Freigabe | Entscheidung |
| 3 | **Testkorpus**: 8–10 synthetische Bescheide über die v1-Matrix, je als sauberes PDF **und** als Handyfoto-Variante (schief, Schatten) | Mocks generieren, ausdrucken, abfotografieren; Fall K anonymisiert als Realanker | 1–2 Sessions + dein Drucker/Handy |
| 4 | **Steuer-Engine** + Testsuite | bauen; BMF-Rechner als Referenz | 2–3 Sessions |
| 5 | **Wirkungsdaten-Paket**: COFOG-Ist je Ebene (der bekannte größte Restposten), feste Einheiten je Kategorie, Delta-Vorjahr | Destatis/GENESIS-Export + bundeshaushalt.de; bis dahin läuft der Prototyp mit den verifizierten 2023-Anteilen, gekennzeichnet | Recherche, parallel |
| 6 | **Template-Generalisierung** Fall-K-HTML → Jinja2 mit Bausteinen | bauen | 2 Sessions |
| 7 | **Extraktions-Layer** + Validierungsschleife | bauen; braucht Anthropic-API-Key für den Standalone-Betrieb | 1–2 Sessions |
| 8 | **Web-Shell** (Upload → Review → Bescheid → PDF) | bauen | 1–2 Sessions |
| 9 | **Datenschutz-Setup** (s. u.) | Entscheidung + Umsetzung | Entscheidung |

**Baureihenfolge:** 1→2 (Fundament) · 4 parallel zu 3 · dann 7 (Extraktion gegen Testkorpus, Engine validiert) · dann 6+8 · 5 läuft parallel und wird als Datenpaket eingesteckt.

---

## 6. Datenschutz (nicht verhandelbar, da echte Steuerdaten)

Ein hochgeladener Echtbescheid enthält Name, Adresse, Steuer-ID, IdNr. der Kinder, Bankverbindung. Vorschlag für den Demonstrator:

1. **Keine Persistenz:** Upload und Extraktionsergebnis werden nach Session-Ende gelöscht; nichts wird geloggt.
2. **Maskierung vor Verarbeitung:** Steuer-ID/IdNr./IBAN werden extrahiert, aber sofort verworfen — das Schema enthält sie gar nicht erst.
3. **API-Weg:** Anthropic API mit DPA/Zero-Retention; im Upload-Screen transparent erklärt. Alternative für maximale Vorsicht: Testphase nur mit synthetischen Bescheiden + Fall K, Echtbescheide erst nach Einwilligungs-Setup.
4. **Disclaimer:** „Modellrechnung, keine steuerliche Beratung, ersetzt nicht den Bescheid" — passt zur P2-Beilagen-Logik.

---

## 7. Entscheidungen (Teresa, 13.07.2026)

1. **Fallmatrix:** v2 wird vollständig in v1 integriert — der Prototyp deckt von Anfang an auch selbständige/gewerbliche Einkünfte, Verlustabzug, ausländische Einkünfte/DBA-PV, Faktorverfahren, Änderungsbescheide und Unterhalt/Realsplitting ab.
2. **Betriebsmodell:** Cloud-gehostet (nicht lokal). Datenschutz-Setup aus Abschn. 6 wird damit Pflichtbestandteil vor Go-Live.
3. **Soli:** wird ins Wirkungsmodell einbezogen (fließt zu 100 % dem Bund zu, Art. 106 Abs. 1 Nr. 6 GG — kein Drei-Ebenen-Split). **Kirchensteuer:** eigener Ausweis-Baustein: „Ihr Beitrag zu Ihrer Konfessionsgemeinschaft — der Staat hat keine Verfügung über diese Mittel." Kein Wirkungsmodell, keine COFOG-Zuordnung.
4. **Indikator-Datierung:** aktuellste verifizierte Werte, je Wert gekennzeichnet mit „bezogen auf Jahr X".
5. **Startpunkt:** Schema + Steuer-Engine + Fall-K-Golden-Test (in Umsetzung).
