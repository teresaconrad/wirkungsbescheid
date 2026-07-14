"""
Korpus-Generator: baut aus FallDefs engine-konsistente Bescheid-Objekte (Golden JSON).
Alle Ketten laufen durch die Steuer-Engine — dieselben Regeln, mit denen später
extrahierte Bescheide validiert werden. Jeder generierte Fall besteht nachrechnen().
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR

from ..engine import (steuer_mit_pv, zumutbare_belastung, guenstigerpruefung,
                      ermaessigung_35a, soli as soli_fn)
from ..models import (Bescheid, Meta, Bescheidart, Veranlagungsart, EinkuenftePerson,
                      Abzuege, Festsetzung, Abrechnung, Betrag, Kind)
from .faelle import FallDef, PersonDef, KFB_JE_KIND_2024

D = Decimal
KIST_SATZ = {"Bayern": D("0.08"), "Baden-Württemberg": D("0.08")}  # sonst 9 %


def _floor(x: Decimal) -> Decimal:
    return D(x).quantize(D("1"), rounding=ROUND_FLOOR)


def _cent(x: Decimal) -> Decimal:
    return D(x).quantize(D("0.01"), rounding=ROUND_FLOOR)


def _person(p: PersonDef) -> tuple[EinkuenftePerson, Decimal]:
    nsa = max(p.brutto - p.wk, D("0")) if p.brutto > 0 else D("0")
    summe = nsa + p.kapital_tariflich + p.vuv + p.selbstaendig + p.gewerbebetrieb + p.renten
    ep = EinkuenftePerson(
        bruttolohn=Betrag.von(p.brutto) if p.brutto else None,
        werbungskosten=Betrag.von(p.wk) if p.wk else None,
        einkuenfte_nsa=Betrag.von(nsa) if nsa else None,
        kapital_tariflich=Betrag.von(p.kapital_tariflich) if p.kapital_tariflich else None,
        vermietung_verpachtung=Betrag.von(p.vuv) if p.vuv else None,
        selbstaendig=Betrag.von(p.selbstaendig) if p.selbstaendig else None,
        gewerbebetrieb=Betrag.von(p.gewerbebetrieb) if p.gewerbebetrieb else None,
        gewerbesteuer_messbetrag=Betrag.von(p.gewst_messbetrag) if p.gewst_messbetrag else None,
        renten_besteuerungsanteil=Betrag.von(p.renten) if p.renten else None,
        lohnersatzleistungen=Betrag.von(p.lohnersatz) if p.lohnersatz else None,
        auslaendische_einkuenfte_dba=Betrag.von(p.dba_auslandseinkuenfte) if p.dba_auslandseinkuenfte else None,
        lohnsteuer_einbehalten=Betrag.von(p.lohnsteuer) if p.lohnsteuer else None,
        faktorverfahren=p.faktorverfahren,
    )
    return ep, summe


def generiere(f: FallDef) -> Bescheid:
    pa, eink_a = _person(f.person_a)
    pb, eink_b = (None, D("0"))
    if f.person_b is not None:
        pb, eink_b = _person(f.person_b)
    gde = eink_a + eink_b

    # außergewöhnliche Belastungen
    zb = zumutbare_belastung(gde, f.zusammen, f.kinder) if f.agb_geltend > 0 else D("0")
    agb_abziehbar = max(f.agb_geltend - zb, D("0"))

    abzuege_summe = (f.vorsorge + f.spenden + f.kinderbetreuung + f.unterhalt_realsplitting
                     + f.ausbildungsfreibetrag + f.verlustabzug + agb_abziehbar)
    einkommen = _floor(gde - abzuege_summe)

    fb = D(f.kinder) * KFB_JE_KIND_2024
    pv = ((f.person_a.lohnersatz + f.person_a.dba_auslandseinkuenfte)
          + (f.person_b.lohnersatz + f.person_b.dba_auslandseinkuenfte if f.person_b else D("0")))

    # Günstigerprüfung (§ 31)
    hinzurechnung = D("0")
    zve = einkommen
    if f.kinder > 0:
        erg = guenstigerpruefung(einkommen - fb, fb, f.kindergeld_erhalten,
                                 pv, f.jahr, f.zusammen)
        if erg.freibetraege_guenstiger:
            zve = einkommen - fb
            hinzurechnung = f.kindergeld_erhalten

    tarifliche, satz = steuer_mit_pv(zve, pv, f.jahr, f.zusammen)
    erm_35a = ermaessigung_35a(f.p35a_haushaltsnah, f.p35a_handwerker)
    messbetrag = (f.person_a.gewst_messbetrag
                  + (f.person_b.gewst_messbetrag if f.person_b else D("0")))
    erm_35 = min(D("4") * messbetrag, tarifliche) if messbetrag > 0 else D("0")
    festgesetzt = max(tarifliche + hinzurechnung - erm_35a - erm_35, D("0"))

    # Soli/KiSt-Bemessung: stets mit Kinderfreibeträgen (§ 3 Abs. 2a SolZG, § 51a EStG)
    steuer_mit_fb, _ = steuer_mit_pv(einkommen - fb, pv, f.jahr, f.zusammen)
    bmg = max(steuer_mit_fb - erm_35a - erm_35, D("0"))
    soli_betrag = soli_fn(bmg, f.jahr, f.zusammen)
    kist = _cent(KIST_SATZ.get(f.bundesland, D("0.09")) * bmg) if f.kirchensteuer else D("0")

    lst = (f.person_a.lohnsteuer + (f.person_b.lohnsteuer if f.person_b else D("0")))
    gezahlt = lst + f.vz_geleistet
    saldo = gezahlt - festgesetzt - soli_betrag - kist

    # künftige Vorauszahlungen bei Gewinneinkünften/hoher verbleibender Steuer
    verbleibend = festgesetzt + soli_betrag - lst
    vz_quartal = _floor(verbleibend / D("4")) if verbleibend > D("400") and (
        f.person_a.selbstaendig or f.person_a.gewerbebetrieb or f.person_a.vuv
        or f.person_a.renten
        or (f.person_b and (f.person_b.selbstaendig or f.person_b.gewerbebetrieb
                            or f.person_b.vuv))) else D("0")

    return Bescheid(
        meta=Meta(finanzamt=f.finanzamt, veranlagungsjahr=f.jahr,
                  anrede=f.anrede or None,
                  bescheiddatum="15.05.2026", bundesland=f.bundesland,
                  bescheidart=(Bescheidart.aenderungsbescheid if f.aenderungsbescheid
                               else Bescheidart.erstbescheid),
                  vorlaeufigkeitsvermerke=list(f.vorlaeufigkeit)),
        veranlagungsart=Veranlagungsart.zusammen if f.zusammen else Veranlagungsart.einzel,
        kirchensteuerpflicht=f.kirchensteuer,
        kinder=[Kind(freibetrag=Betrag.von(KFB_JE_KIND_2024)) for _ in range(f.kinder)],
        person_a=pa, person_b=pb,
        abzuege=Abzuege(
            vorsorgeaufwendungen=Betrag.von(f.vorsorge) if f.vorsorge else None,
            spenden=Betrag.von(f.spenden) if f.spenden else None,
            kinderbetreuung=Betrag.von(f.kinderbetreuung) if f.kinderbetreuung else None,
            unterhalt_realsplitting=Betrag.von(f.unterhalt_realsplitting) if f.unterhalt_realsplitting else None,
            agb_geltend_gemacht=Betrag.von(f.agb_geltend) if f.agb_geltend else None,
            agb_zumutbare_belastung=Betrag.von(zb) if f.agb_geltend else None,
            agb_abziehbar=Betrag.von(agb_abziehbar) if f.agb_geltend else None,
            ausbildungsfreibetrag=Betrag.von(f.ausbildungsfreibetrag) if f.ausbildungsfreibetrag else None,
            verlustabzug=Betrag.von(f.verlustabzug) if f.verlustabzug else None,
            p35a_haushaltsnah=Betrag.von(f.p35a_haushaltsnah) if f.p35a_haushaltsnah else None,
            p35a_handwerker=Betrag.von(f.p35a_handwerker) if f.p35a_handwerker else None,
        ),
        festsetzung=Festsetzung(
            gesamtbetrag_einkuenfte=Betrag.von(gde),
            einkommen=Betrag.von(einkommen),
            kinderfreibetraege_summe=Betrag.von(fb) if fb else None,
            zve=Betrag.von(zve),
            steuersatz_besonders=satz if satz != 0 else None,
            tarifliche_est=Betrag.von(tarifliche),
            hinzurechnung_kindergeld=Betrag.von(hinzurechnung) if hinzurechnung else None,
            ermaessigung_35a=Betrag.von(erm_35a) if erm_35a else None,
            ermaessigung_35=Betrag.von(erm_35) if erm_35 else None,
            festgesetzte_est=Betrag.von(festgesetzt),
            soli=Betrag.von(soli_betrag),
            kirchensteuer=Betrag.von(kist) if f.kirchensteuer else None,
        ),
        abrechnung=Abrechnung(
            lohnsteuer_gesamt=Betrag.von(lst) if lst else None,
            vorauszahlungen_geleistet=Betrag.von(f.vz_geleistet) if f.vz_geleistet else None,
            erstattung=Betrag.von(saldo) if saldo > 0 else None,
            nachzahlung=Betrag.von(-saldo) if saldo < 0 else None,
            vorauszahlungen_kuenftig_quartal=Betrag.von(vz_quartal) if vz_quartal else None,
        ),
    )
