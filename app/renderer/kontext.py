"""
Kontext-Builder: Bescheid → Template-Kontext für den Kombi-Bescheid.
Alle Zahlen kommen aus der Engine (nachgerechnet), dem Wirkungsmodell und der Fall-Logik.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from ..models import Bescheid, Veranlagungsart
from ..engine import (nachrechnen, guenstigerpruefung, splitting_vorteil, pv_effekt,
                      soli_ersparnis, soli_voll, steuer_mit_pv)
from ..engine.soli import FREIGRENZEN
from ..falllogik import fallmerkmale
from ..wirkung import (ebenen_split, kategorien, kreislauf, kirchensteuer_baustein,
                       deltas, methodik_link)

D = Decimal

# Gesetzliches Kindergeld je Kind und Jahr (§ 66 EStG): 2023/2024 je 250 €/Monat,
# 2025: 255 €/Monat, 2026: 259 €/Monat. Wird genutzt, wenn das Kindergeld günstiger
# war und deshalb NICHT als Hinzurechnung im Bescheid steht — der Jahresbetrag ist
# dann trotzdem aus Kinderzahl + Gesetz ableitbar (P9: verifizierter Rechtswert).
KINDERGELD_JAHR_JE_KIND = {2023: D("3000"), 2024: D("3000"),
                           2025: D("3060"), 2026: D("3108")}


def euro(x, cents: bool = False) -> str:
    if x is None:
        return "—"
    d = D(str(x.wert if hasattr(x, "wert") else x))
    s = f"{d:,.2f}" if cents or d != d.to_integral_value() else f"{d:,.0f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _w(b) -> Decimal | None:
    return b.wert if b is not None else None


def _zeilen_einkuenfte(b: Bescheid) -> list[dict]:
    felder = [
        ("bruttolohn", "Bruttoarbeitslohn", "laut Lohnsteuerbescheinigung", False),
        ("werbungskosten", "minus Werbungskosten", "Arbeitsweg, Arbeitsmittel, Fortbildung (§ 9 EStG)", True),
        ("kapital_tariflich", "Kapitalerträge (tariflich)", "werden mit dem normalen Tarif besteuert — siehe Kasten", False),
        ("vermietung_verpachtung", "Vermietung & Verpachtung", "Überschuss aus vermieteter Immobilie (§ 21 EStG)", False),
        ("selbstaendig", "Selbständige Arbeit", "Gewinn (§ 18 EStG)", False),
        ("gewerbebetrieb", "Gewerbebetrieb", "Gewinn (§ 15 EStG); die Gewerbesteuer wird angerechnet — siehe Berechnung Teil 2", False),
        ("renten_besteuerungsanteil", "Renten (Besteuerungsanteil)", "nur der steuerpflichtige Anteil Ihrer Rente (§ 22 EStG)", False),
    ]
    zeilen = []
    for attr, label, sub, neg in felder:
        va, vb = _w(getattr(b.person_a, attr)), \
                 _w(getattr(b.person_b, attr)) if b.person_b else None
        if va is None and vb is None:
            continue
        zeilen.append({"label": label, "sub": sub, "neg": neg,
                       "a": euro(va) if va is not None else "—",
                       "b": euro(vb) if vb is not None else "—"})
    return zeilen


def _zeilen_abzuege(b: Bescheid) -> list[dict]:
    a = b.abzuege
    kandidaten = [
        (a.vorsorgeaufwendungen, "Vorsorgeaufwendungen", "Renten-, Kranken- und Pflegeversicherung (§ 10 EStG)"),
        (a.spenden, "Spenden & Mitgliedsbeiträge", "Zuwendungen nach § 10b EStG"),
        (a.kinderbetreuung, "Kinderbetreuungskosten", "§ 10 Abs. 1 Nr. 5 EStG"),
        (a.unterhalt_realsplitting, "Unterhaltsleistungen (Realsplitting)", "an geschiedene/getrennt lebende Ehepartner:in, § 10 Abs. 1a EStG — siehe Kasten"),
        (a.verlustabzug, "Verlustabzug aus Vorjahren", "§ 10d EStG — siehe Kasten"),
        (a.ausbildungsfreibetrag, "Auswärts wohnendes Kind in Ausbildung", "Freibetrag § 33a Abs. 2 EStG"),
        (a.agb_abziehbar, "Außergewöhnliche Belastungen (wirksamer Teil)", "z. B. Krankheitskosten oberhalb der zumutbaren Belastung — siehe Kasten"),
    ]
    return [{"label": l, "sub": s, "wert": euro(v.wert)}
            for v, l, s in kandidaten if v is not None and v.wert != 0]


def baue_kontext(b: Bescheid) -> dict:
    m = fallmerkmale(b)
    nr = nachrechnen(b)
    f = b.festsetzung
    jahr = b.meta.veranlagungsjahr
    splitting = b.veranlagungsart == Veranlagungsart.zusammen
    pv = b.lohnersatz_gesamt()
    zve = _w(f.zve) or D("0")
    est = _w(f.festgesetzte_est) or D("0")
    soli_w = _w(f.soli) or D("0")
    kist_w = _w(f.kirchensteuer) or D("0")

    # --- Abrechnung
    gezahlt = ((_w(b.abrechnung.lohnsteuer_gesamt) or D("0"))
               + (_w(b.abrechnung.vorauszahlungen_geleistet) or D("0"))
               + (_w(b.abrechnung.bereits_getilgt) or D("0")))
    erstattung = _w(b.abrechnung.erstattung)
    nachzahlung = _w(b.abrechnung.nachzahlung)

    # --- „Ihr Jahr in X Zahlen"
    zahlen: list[dict] = []
    if m["soli_faellt_an"] or (soli_w == 0 and (nr.tarifliche_est or 0) > 0):
        ersparnis = soli_ersparnis(max((nr.tarifliche_est or D("0")), D("0")), jahr, splitting)
        if ersparnis > 0:
            grund = ("weil Ihre Steuer in der Soli-Gleitzone liegt" if soli_w > 0
                     else "Soli gespart — Sie liegen unter der Freigrenze")
            zahlen.append({"wert": euro(ersparnis, True), "label": f"weniger Solidaritätszuschlag, {grund}", "gruen": True})
    # Kindergeld: im Bescheid nur sichtbar, wenn Freibeträge günstiger waren
    # (Hinzurechnung). Sonst aus Kinderzahl × gesetzlichem Jahresbetrag abgeleitet.
    kg = _w(f.hinzurechnung_kindergeld) or D("0")
    kg_abgeleitet = False
    kg_jahr = kg
    if not kg_jahr and m["kinder"] and jahr in KINDERGELD_JAHR_JE_KIND:
        kg_jahr = KINDERGELD_JAHR_JE_KIND[jahr] * len(b.kinder)
        kg_abgeleitet = True
    kindervorteil = None
    if m["kinder"]:
        fb = _w(f.kinderfreibetraege_summe) or D("0")
        einkommen = _w(f.einkommen) or zve
        gp = guenstigerpruefung(einkommen - fb, fb, kg_jahr, pv, jahr, splitting)
        kindervorteil = gp
        netto = gp.steuervorteil_freibetraege - kg if kg else gp.kindergeld
        if gp.freibetraege_guenstiger and netto > 0:
            zahlen.append({"wert": euro(netto), "label": "Steuer-Entlastung durch Ihre Kinder — zusätzlich zum Kindergeld", "gruen": False})
    if m["progressionsvorbehalt"] or m["dba_auslandseinkuenfte"]:
        effekt = pv_effekt(zve, pv, jahr, splitting)
        zahlen.append({"wert": euro(effekt), "label": "Mehrsteuer durch den Progressionsvorbehalt (Berechnung Teil 2)", "gruen": False})
    sv = None
    if splitting:
        gde = _w(f.gesamtbetrag_einkuenfte)
        anteil_a = D("0.5")
        if gde and gde > 0:
            summe_a = sum((_w(getattr(b.person_a, x)) or D("0")) for x in
                          ("einkuenfte_nsa", "kapital_tariflich", "vermietung_verpachtung",
                           "selbstaendig", "gewerbebetrieb", "renten_besteuerungsanteil"))
            anteil_a = (summe_a / gde).quantize(D("0.01"), rounding=ROUND_HALF_UP)
        pv_a = ((_w(b.person_a.lohnersatzleistungen) or D("0"))
                + (_w(b.person_a.auslaendische_einkuenfte_dba) or D("0")))
        sv = {"vorteil": splitting_vorteil(zve, anteil_a, pv_a, pv - pv_a, jahr),
              "anteil_a": int(anteil_a * 100)}
        if sv["vorteil"] > 0:
            zahlen.append({"wert": euro(sv["vorteil"]), "label": "Ihr Splitting-Vorteil gegenüber zwei Einzelveranlagungen (Näherung)", "gruen": False})
    if erstattung:
        zahlen.append({"wert": euro(erstattung, True), "label": "kommen als Erstattung zu Ihnen zurück", "gruen": True})

    # --- Wirkungsteil: Basis = ESt + Soli (Entscheidung 13.07.2026)
    basis = est + soli_w
    split = ebenen_split(est, soli_w, b.meta.bundesland)
    kats = kategorien(basis)
    max_betrag = max((k.betrag for k in kats), default=D("1")) or D("1")
    # Fußnoten (P9): Kostensätze mit Einschränkung (regionaler Satz, eigene
    # Ableitung) werden hochgestellt markiert und unter der Liste erläutert.
    fussnoten: list[str] = []
    ZIFFERN = "¹²³⁴⁵⁶⁷⁸⁹"

    def _mit_fussnote(text: str, fn: str | None) -> str:
        if not fn:
            return text
        if fn not in fussnoten:
            fussnoten.append(fn)
        return text + ZIFFERN[fussnoten.index(fn)]

    kat_ctx = [{
        "name": k.name, "anteil": f"{(k.anteil * 100).quantize(D('0.1'))} %".replace(".", ","),
        "euro": euro(k.betrag), "breite": f"{(k.anteil * 100)}",
        "balken": f"{(k.betrag / max_betrag * 100).quantize(D('1'))}",
        "verifiziert": k.verifiziert, "quelle": k.quelle, "hinweis": k.hinweis,
        "einheiten": [
            {"text": _mit_fussnote(
                (f"{str(e['anzahl']).replace('.', ',')} × {e['einheit']}"
                 if e["anzahl"] is not None else e["einheit"]), e.get("fussnote")),
             "label": e["label"] + (f" · {e['basis_zusatz']}" if e.get("basis_zusatz") else "")}
            for e in k.einheiten],
    } for k in kats]
    wirkung_fussnoten = [f"{ZIFFERN[i]} {t}" for i, t in enumerate(fussnoten)]
    delta_ctx = deltas(basis)

    beitrag_soziales = next((k.betrag for k in kats if k.id == "soziale_sicherung"), D("0"))
    # Rückfluss = Kindergeld (verrechnet ODER gesetzlich abgeleitet) + echte
    # Lohnersatzleistungen. DBA-Auslandseinkünfte zählen NICHT — sie sind
    # Progressionsvorbehalt, aber keine Sozialleistung.
    lohnersatz_sozial = sum(((_w(p.lohnersatzleistungen) or D("0"))
                             for p in [b.person_a, b.person_b] if p is not None),
                            D("0"))
    zurueck = kg_jahr + lohnersatz_sozial
    kreis = kreislauf(beitrag_soziales, zurueck) if zurueck > 0 else None

    # --- Soli-Erklärbox
    soli_box = None
    if soli_w > 0:
        fg = FREIGRENZEN[jahr][1 if splitting else 0]
        voll = soli_voll(max((nr.tarifliche_est or D("0")), D("0")))
        if soli_w < voll:
            ueber = (nr.tarifliche_est or D("0")) - fg
            soli_box = {"ueber": euro(ueber), "voll": euro(voll, True),
                        "ersparnis": euro(voll - soli_w, True)}

    # Einheitliches Anrede-Schema (Textbuch 13_standardtexte.md, ID A1/A2):
    # mit Namen „Liebe Familie X" / „Liebe/r Frau/Herr X" (aus meta.anrede),
    # ohne Namen die neutrale Standard-Anrede — identisch über alle Fälle.
    anrede = b.meta.anrede or "Liebe Steuerzahlerin, lieber Steuerzahler"

    return {
        "b": b, "m": m, "f": f, "euro": euro, "jahr": jahr, "splitting": splitting,
        "anrede": anrede,
        "nachrechnung": nr,
        "validiert": nr.validiert,
        "zve": euro(zve), "tarifliche": euro(nr.tarifliche_est),
        "steuersatz": (str(f.steuersatz_besonders).replace(".", ",") + " %"
                       if f.steuersatz_besonders else None),
        "pv_summe": euro(pv) if pv else None,
        "pv_effekt": euro(pv_effekt(zve, pv, jahr, splitting)) if pv else None,
        "festgesetzt_gesamt": euro(est + soli_w + kist_w, True),
        "gezahlt": euro(gezahlt, True),
        "erstattung": euro(erstattung, True) if erstattung else None,
        "nachzahlung": euro(nachzahlung, True) if nachzahlung else None,
        "vz_quartal": (euro(b.abrechnung.vorauszahlungen_kuenftig_quartal)
                       if m["vorauszahlungen_kuenftig"] else None),
        "zahlen": zahlen[:5],
        "einkuenfte_zeilen": _zeilen_einkuenfte(b),
        "abzuege_zeilen": _zeilen_abzuege(b),
        "kindervorteil": kindervorteil,
        "splitting_info": sv,
        "soli_box": soli_box,
        "kist": euro(kist_w, True) if kist_w else None,
        "kist_baustein": kirchensteuer_baustein(),
        "split": split, "basis": euro(basis, True),
        "kategorien": kat_ctx,
        "wirkung_fussnoten": wirkung_fussnoten,
        "methodik_link": methodik_link(),
        "deltas": delta_ctx,
        "kreislauf": kreis,
        "kg_erhalten": euro(kg_jahr) if kg_jahr else None,
        "kg_abgeleitet": kg_abgeleitet,
        "lohnersatz": euro(lohnersatz_sozial) if lohnersatz_sozial else None,
    }
