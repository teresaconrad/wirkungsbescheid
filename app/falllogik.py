"""
Fall-Erkennung (Stufe 4, P16): Fallmerkmale → aktivierte Render-Bausteine.
Vollständige Matrix (v1 inkl. der früheren v2-Merkmale, Entscheidung 13.07.2026).
"""
from __future__ import annotations

from .models import Bescheid, Veranlagungsart, Bescheidart


def fallmerkmale(b: Bescheid) -> dict[str, bool]:
    f, a = b.festsetzung, b.abzuege

    def hat(betrag) -> bool:
        return betrag is not None and betrag.wert != 0

    personen = [p for p in [b.person_a, b.person_b] if p is not None]
    return {
        "zusammenveranlagung": b.veranlagungsart == Veranlagungsart.zusammen,
        "erstattung": hat(b.abrechnung.erstattung),
        "nachzahlung": hat(b.abrechnung.nachzahlung),
        "kinder": b.anzahl_kinder() > 0,
        "guenstigerpruefung_kindergeld": hat(f.hinzurechnung_kindergeld),
        "progressionsvorbehalt": b.lohnersatz_gesamt() != 0,
        "dba_auslandseinkuenfte": any(hat(p.auslaendische_einkuenfte_dba) for p in personen),
        "kapital_tariflich": any(hat(p.kapital_tariflich) for p in personen),
        "vermietung": any(hat(p.vermietung_verpachtung) for p in personen),
        "selbstaendig_gewerblich": any(hat(p.selbstaendig) or hat(p.gewerbebetrieb) for p in personen),
        "gewerbesteuer_anrechnung": any(hat(p.gewerbesteuer_messbetrag) for p in personen),
        "renten": any(hat(p.renten_besteuerungsanteil) for p in personen),
        "faktorverfahren": any(p.faktorverfahren for p in personen),
        "verlustabzug": hat(a.verlustabzug),
        "unterhalt_realsplitting": hat(a.unterhalt_realsplitting),
        "agb_zumutbare_belastung": hat(a.agb_geltend_gemacht),
        "p35a": hat(a.p35a_haushaltsnah) or hat(a.p35a_handwerker),
        "soli_faellt_an": hat(f.soli),
        "kirchensteuer": b.kirchensteuerpflicht or hat(f.kirchensteuer),
        "vorlaeufigkeit": len(b.meta.vorlaeufigkeitsvermerke) > 0,
        "vorauszahlungen_kuenftig": hat(b.abrechnung.vorauszahlungen_kuenftig_quartal),
        "aenderungsbescheid": b.meta.bescheidart == Bescheidart.aenderungsbescheid,
    }


# Mapping Merkmal → „Was heißt das?"-Boxen und Seitenmodule (für den Renderer)
BAUSTEINE: dict[str, list[str]] = {
    "zusammenveranlagung": ["box_splitting", "zeile_wer_zahlt_was_im_paar", "berechnung_zweispaltig"],
    "erstattung": ["modul_erstattung"],
    "nachzahlung": ["modul_nachzahlung", "modul_zahlungsfolgen"],
    "kinder": ["box_kinderfreibetraege"],
    "guenstigerpruefung_kindergeld": ["box_guenstigerpruefung"],
    "progressionsvorbehalt": ["box_progressionsvorbehalt"],
    "dba_auslandseinkuenfte": ["box_dba_progressionsvorbehalt"],
    "kapital_tariflich": ["box_kapital_tariflich"],
    "vermietung": ["zeile_vermietung"],
    "selbstaendig_gewerblich": ["box_gewinneinkuenfte"],
    "gewerbesteuer_anrechnung": ["box_p35_gewerbesteuer"],
    "renten": ["box_renten_besteuerungsanteil"],
    "faktorverfahren": ["box_faktorverfahren"],
    "verlustabzug": ["box_verlustabzug"],
    "unterhalt_realsplitting": ["box_realsplitting"],
    "agb_zumutbare_belastung": ["box_zumutbare_belastung"],
    "p35a": ["box_p35a"],
    "soli_faellt_an": ["box_soli_milderungszone"],
    "kirchensteuer": ["baustein_kirchensteuer_konfession"],
    "vorlaeufigkeit": ["box_vorlaeufigkeit_kurz"],
    "vorauszahlungen_kuenftig": ["modul_vorauszahlungen"],
    "aenderungsbescheid": ["box_aenderungsbescheid"],
}


def aktive_bausteine(b: Bescheid) -> list[str]:
    merkmale = fallmerkmale(b)
    aktiv: list[str] = []
    for merkmal, an in merkmale.items():
        if an:
            aktiv.extend(BAUSTEINE.get(merkmal, []))
    return aktiv
