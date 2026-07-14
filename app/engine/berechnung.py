"""
Nachrechnung — das Herzstück der Extraktions-Validierung (Stufe 3 des Blueprints).

Aus den extrahierten Eingangsgrößen (zvE, PV-Einkünfte, Freibeträge, Hinzurechnung,
Ermäßigungen) wird die festgesetzte Steuer deterministisch nachgerechnet und mit den
extrahierten Werten verglichen. Übereinstimmung auf den Euro ⇒ Extraktion validiert.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from ..models import Bescheid, Veranlagungsart
from .progression import steuer_mit_pv
from .soli import soli

D = Decimal


@dataclass
class Abweichung:
    feld: str
    extrahiert: Decimal
    berechnet: Decimal

    @property
    def differenz(self) -> Decimal:
        return self.extrahiert - self.berechnet


@dataclass
class Nachrechnung:
    tarifliche_est: Optional[Decimal] = None
    steuersatz_besonders: Optional[Decimal] = None
    festgesetzte_est: Optional[Decimal] = None
    soli: Optional[Decimal] = None
    abweichungen: list[Abweichung] = field(default_factory=list)

    @property
    def validiert(self) -> bool:
        return len(self.abweichungen) == 0


def _w(betrag) -> Optional[Decimal]:
    return betrag.wert if betrag is not None else None


def nachrechnen(b: Bescheid) -> Nachrechnung:
    """Rechnet die Festsetzung aus extrahierten Basiswerten nach und vergleicht."""
    f = b.festsetzung
    jahr = b.meta.veranlagungsjahr
    splitting = b.veranlagungsart == Veranlagungsart.zusammen
    erg = Nachrechnung()

    zve = _w(f.zve)
    if zve is None:
        return erg  # ohne zvE keine Nachrechnung möglich → Extraktion unvollständig

    pv = b.lohnersatz_gesamt()
    tarifliche, satz = steuer_mit_pv(zve, pv, jahr, splitting)
    erg.tarifliche_est = tarifliche
    erg.steuersatz_besonders = satz

    hinzurechnung = _w(f.hinzurechnung_kindergeld) or D("0")
    erm = (_w(f.ermaessigung_35a) or D("0")) + (_w(f.ermaessigung_35) or D("0"))
    festgesetzt = tarifliche + hinzurechnung - erm
    erg.festgesetzte_est = festgesetzt

    # Soli-BMG: ESt mit Kinderfreibeträgen, ohne Kindergeld-Hinzurechnung (§ 3 Abs. 2a SolZG).
    # War Kindergeld günstiger (keine Hinzurechnung), sind die Freibeträge NICHT im zvE —
    # für den Soli werden sie fiktiv abgezogen (Einkommen − Freibeträge).
    kfb = _w(f.kinderfreibetraege_summe) or D("0")
    einkommen = _w(f.einkommen)
    if kfb > 0 and hinzurechnung == 0 and einkommen is not None:
        steuer_soli, _ = steuer_mit_pv(einkommen - kfb, pv, jahr, splitting)
    else:
        steuer_soli = tarifliche
    erg.soli = soli(max(steuer_soli - erm, D("0")), jahr, splitting)

    def vergleiche(feld: str, extrahiert, berechnet: Decimal):
        if extrahiert is not None and D(extrahiert) != berechnet:
            erg.abweichungen.append(Abweichung(feld, D(extrahiert), berechnet))

    vergleiche("tarifliche_est", _w(f.tarifliche_est), tarifliche)
    if f.steuersatz_besonders is not None and satz != 0:
        vergleiche("steuersatz_besonders", f.steuersatz_besonders, satz)
    vergleiche("festgesetzte_est", _w(f.festgesetzte_est), festgesetzt)
    vergleiche("soli", _w(f.soli), erg.soli)
    return erg
