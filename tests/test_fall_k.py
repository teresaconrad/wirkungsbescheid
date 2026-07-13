"""
Golden Case: Fall K (anonymisierter Realbescheid VZ 2024, Doku 09).
Jeder Wert muss auf den Euro/Cent mit dem echten Bescheid übereinstimmen.
"""
from decimal import Decimal

from app.engine import (grundtarif, splittingtarif, steuer_mit_pv, besonderer_steuersatz,
                        soli, soli_voll, zumutbare_belastung, guenstigerpruefung,
                        nachrechnen, pv_effekt, soli_ersparnis)
from app.models import (Bescheid, Meta, Veranlagungsart, EinkuenftePerson, Abzuege,
                        Festsetzung, Abrechnung, Betrag, Kind)
from app.falllogik import fallmerkmale, aktive_bausteine

D = Decimal

ZVE = D("132730")
PV = D("13538")          # Elterngeld 2.550 + 10.988
JAHR = 2024


def test_splitting_haelfte():
    # halbes zvE der PV-Basis 146.268 → 73.134 → 20.079 €, verdoppelt 40.158 €
    assert grundtarif(D("73134"), JAHR) == D("20079")
    assert splittingtarif(D("146268"), JAHR) == D("40158")


def test_besonderer_steuersatz():
    satz = besonderer_steuersatz(ZVE, PV, JAHR, splitting=True)
    assert satz == D("27.4550")  # Bescheid: 27,4550 % (abgeschnitten)


def test_tarifliche_est():
    steuer, satz = steuer_mit_pv(ZVE, PV, JAHR, splitting=True)
    assert steuer == D("36441")
    assert satz == D("27.4550")


def test_soli_milderungszone():
    assert soli(D("36441"), JAHR, splitting=True) == D("21.53")
    assert soli_voll(D("36441")) == D("2004.25")
    assert soli_ersparnis(D("36441"), JAHR, splitting=True) == D("1982.72")


def test_zumutbare_belastung():
    # GdE 176.363, zusammen, 3 Kinder → 3.015 €
    assert zumutbare_belastung(D("176363"), splitting=True, kinder=3) == D("3015")


def test_guenstigerpruefung():
    erg = guenstigerpruefung(zve_mit_fb=ZVE, freibetraege=D("19080"),
                             kindergeld=D("6000"), pv_einkuenfte=PV,
                             jahr=JAHR, splitting=True)
    assert erg.steuer_mit_freibetraegen == D("36441")
    assert erg.freibetraege_guenstiger  # Freibeträge günstiger als 6.000 € Kindergeld
    assert erg.steuervorteil_freibetraege > D("6000")


def test_pv_effekt_positiv():
    effekt = pv_effekt(ZVE, PV, JAHR, splitting=True)
    assert effekt > D("1500")  # Doku 09: überschlägig ~1.900 €
    assert effekt < D("2500")


def _fall_k() -> Bescheid:
    return Bescheid(
        meta=Meta(veranlagungsjahr=2024, bundesland="Berlin",
                  vorlaeufigkeitsvermerke=["Grundfreibetrag", "Kinderfreibeträge"]),
        veranlagungsart=Veranlagungsart.zusammen,
        kinder=[Kind(), Kind(), Kind()],
        person_a=EinkuenftePerson(bruttolohn=Betrag.von(108212),
                                  lohnersatzleistungen=Betrag.von(0)),
        person_b=EinkuenftePerson(bruttolohn=Betrag.von(65861),
                                  vermietung_verpachtung=Betrag.von(4741),
                                  lohnersatzleistungen=Betrag.von(13538)),
        abzuege=Abzuege(agb_geltend_gemacht=Betrag.von(3302),
                        agb_zumutbare_belastung=Betrag.von(3015),
                        agb_abziehbar=Betrag.von(287)),
        festsetzung=Festsetzung(
            gesamtbetrag_einkuenfte=Betrag.von(176363),
            zve=Betrag.von(132730),
            steuersatz_besonders=D("27.4550"),
            tarifliche_est=Betrag.von(36441),
            hinzurechnung_kindergeld=Betrag.von(6000),
            festgesetzte_est=Betrag.von(42441),
            soli=Betrag.von("21.53"),
        ),
        abrechnung=Abrechnung(erstattung=Betrag.von("4205.88"),
                              vorauszahlungen_kuenftig_quartal=Betrag.von(994)),
    )


def test_nachrechnung_validiert():
    """Herzstück: Extraktion gilt als validiert, wenn die Nachrechnung übereinstimmt."""
    erg = nachrechnen(_fall_k())
    assert erg.tarifliche_est == D("36441")
    assert erg.festgesetzte_est == D("42441")
    assert erg.soli == D("21.53")
    assert erg.validiert, [f"{a.feld}: {a.extrahiert} vs {a.berechnet}" for a in erg.abweichungen]


def test_nachrechnung_erkennt_extraktionsfehler():
    b = _fall_k()
    b.festsetzung.zve = Betrag.von(132780)  # OCR-Dreher: 132.730 → 132.780
    erg = nachrechnen(b)
    assert not erg.validiert


def test_falllogik():
    m = fallmerkmale(_fall_k())
    assert m["zusammenveranlagung"] and m["progressionsvorbehalt"]
    assert m["guenstigerpruefung_kindergeld"] and m["erstattung"]
    assert m["vorlaeufigkeit"] and m["vorauszahlungen_kuenftig"]
    assert not m["nachzahlung"] and not m["selbstaendig_gewerblich"]
    bausteine = aktive_bausteine(_fall_k())
    assert "box_progressionsvorbehalt" in bausteine
    assert "modul_zahlungsfolgen" not in bausteine  # Erstattungsfall (P16!)
