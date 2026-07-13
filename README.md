# Wirkungsbescheid-Prototyp — Codebasis

**Stand:** 13.07.2026 · kompletter Durchstich (Upload → Review → Kombi-Bescheid) · 63/63 Tests grün

**Ausprobieren:** `pip install -r requirements.txt` → `uvicorn app.web.main:app` →
http://localhost:8000 (Demo-Modus mit K01–K10 funktioniert ohne API-Key).
Einzelnen Bescheid rendern: `python3 -m app.renderer korpus/K04.json`

## Struktur

```
12_prototyp-blueprint.md   Konzept + Entscheidungen (maßgeblich)
app/
  models.py                Kanonisches Bescheid-Schema (Pydantic, ohne sensible IDs)
  falllogik.py             Fall-Erkennung → konditionale Render-Bausteine (P16)
  engine/                  Deterministische Steuer-Engine (Decimal, amtliche Rundung)
    tarif.py               § 32a Grund-/Splittingtarif 2023–2025
    progression.py         § 32b besonderer Steuersatz (abgeschnitten, 4 Nachkommastellen)
    kinder.py              § 31 Günstigerprüfung Kindergeld/Freibeträge
    soli.py                SolZG Freigrenze + Milderungszone
    agb.py                 § 33 Abs. 3 zumutbare Belastung (stufenweise, BFH)
    ermaessigung.py        § 35a, § 35 (vereinfacht)
    effects.py             „Ihr Jahr in 5 Zahlen"-Kontrafaktuale
    berechnung.py          Nachrechnung = Extraktions-Validierung (Kernmechanik)
  wirkung/
    datenpaket.json        Versionierte Anteile + Einheitskosten (Quelle, Bezugsjahr)
    pipeline.py            Ebenen-Split (Soli→Bund), Kategorien, Einheiten, Kreislauf
  korpus/                  Testkorpus-Generator (python3 -m app.korpus korpus)
    faelle.py              10 Falldefinitionen über die volle Matrix (K01–K10)
    generator.py           Engine-konsistente Zahlenketten → Golden-JSON
    render_alt.py          Alt-Format-Bescheid-PDF (Behörden-Layout, reportlab)
    foto.py                Handyfoto-Degradierung (Schräglage, Rauschen, JPEG)
  extraktion/
    preprocess.py          PDF/JPEG/PNG/HEIC → normalisierte Bilder (+ Textlayer)
    prompt.py              Schema-Prompt (inkl. Datenschutz-Regeln)
    client.py              Claude-Vision-Client mit Nachrechnungs-Korrekturschleife
tests/                     Golden Case Fall K + Eckwerte + Korpus (32 Tests)
korpus/                    Generierter Korpus: K01–K10 als .pdf + .json, Fotos für K01/K04
```

## Verifikationsstatus

- ✅ **Tarif 2024** (Dez-Fassung, GFB 11.784): durch Fall K auf den Euro bestätigt —
  Splitting 73.134 → 20.079 → 40.158; besonderer Steuersatz 27,4550 %; ESt 36.441;
  Soli 21,53; zumutbare Belastung 3.015.
- ⏳ **Tarif 2023/2025**: Parameter hinterlegt, gegen BMF-Steuerrechner zu verifizieren.
- ✅ **Kategorien-Anteile**: alle 11 verifiziert — Eurostat gov_10a_exp (COFOG, DE,
  Gesamtstaat, 2024 vorläufig, Datenstand 27.04.2026, DOI 10.2908/GOV_10A_EXP);
  Zinsen = GF0107 aus GF01 herausgelöst; Verkehr (GF0405) als Unteranteil isoliert.
- ✅ **Vorjahres-Deltas (P7)**: 2023→2024 aus derselben Quelle — Zinsen-Pflichtzeile
  (+22,4 %) + Top-3 mechanisch (Soziales +7,1 %, Gesundheit +5,5 %, Verwaltung +5,8 %).
- ⏳ **Einheitskosten**: 8 verifizierte Einheiten in 3 Kategorien; für Verwaltung,
  Verteidigung, Ordnung, Umwelt, Wohnen, Kultur ehrlich „folgt nach Verifizierung"
  (Beträge und Anteile sind dort trotzdem verifiziert ausgewiesen). Gesundheit
  bewusst ohne Pro-Euro-Einheit (beitragsfinanziert).

## Nächste Bausteine (Reihenfolge lt. Blueprint Abschn. 5)

1. ~~Testkorpus~~ ✅ (K01–K10, alle engine-konsistent; Matrix-Abdeckungstest grün)
2. ~~Extraktions-Layer~~ ✅ gebaut — Live-Test braucht ANTHROPIC_API_KEY
3. ~~Template-Generalisierung~~ ✅ (app/renderer/, Design des Fall-K-Mocks, alle
   Bausteine konditional; app/web/ Review-Screen mit Korrekturschleife)
4. ~~Web-Shell + E2E-Durchstich~~ ✅ (Demo-Modus komplett ohne Key lauffähig)
5. **Live-Extraktionstest** gegen Korpus-PDFs + Fotos (braucht Key)
6. **Cloud-Deployment**: Dockerfile liegt bei — Plattform wählen (Empfehlung Railway),
   ANTHROPIC_API_KEY als Secret setzen, deployen
7. PDF-Export über die bestehende Playwright-Pipeline (bis dahin: Browser-Druck)
8. Daten-Restarbeit (nicht blockierend): COFOG-Vollexport, Tarif 2023/2025 verifizieren,
   Vorjahres-Deltas befüllen

## Tests ausführen

```
pip install -r requirements.txt
python3 -m pytest tests/
```
