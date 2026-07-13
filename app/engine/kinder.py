"""
§ 31 EStG — Günstigerprüfung Kindergeld vs. Kinderfreibeträge.

v1-Vereinfachung: aggregierte Prüfung über alle Kinder (amtlich wird je Kind geprüft);
für die Erklär- und Bezifferungszwecke des Demonstrators ausreichend, als Näherung
gekennzeichnet, sobald Kinder unterschiedliche Freibetragsansätze haben.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .progression import steuer_mit_pv

D = Decimal


@dataclass
class GuenstigerErgebnis:
    steuer_mit_freibetraegen: Decimal
    steuer_ohne_freibetraege: Decimal
    steuervorteil_freibetraege: Decimal   # Differenz der Tarifsteuern
    kindergeld: Decimal
    freibetraege_guenstiger: bool
    netto_kindervorteil: Decimal          # was die Familie durch Kinder insgesamt spart
    naeherung: bool = False


def guenstigerpruefung(zve_mit_fb: Decimal, freibetraege: Decimal, kindergeld: Decimal,
                       pv_einkuenfte: Decimal, jahr: int, splitting: bool,
                       naeherung: bool = False) -> GuenstigerErgebnis:
    """
    zve_mit_fb: zvE nach Abzug der Kinderfreibeträge.
    freibetraege: Summe der angesetzten Kinderfreibeträge.
    kindergeld: verrechnetes Kindergeld (Hinzurechnungsbetrag lt. Bescheid).
    """
    zve_mit_fb, freibetraege, kindergeld = D(zve_mit_fb), D(freibetraege), D(kindergeld)
    steuer_mit, _ = steuer_mit_pv(zve_mit_fb, pv_einkuenfte, jahr, splitting)
    steuer_ohne, _ = steuer_mit_pv(zve_mit_fb + freibetraege, pv_einkuenfte, jahr, splitting)
    vorteil = steuer_ohne - steuer_mit
    guenstiger = vorteil > kindergeld
    # Netto-Kindervorteil: bei Freibeträgen = Steuervorteil (Kindergeld wird verrechnet,
    # war aber schon ausgezahlt) → wirtschaftlich: max(vorteil, kindergeld)
    netto = max(vorteil, kindergeld)
    return GuenstigerErgebnis(
        steuer_mit_freibetraegen=steuer_mit,
        steuer_ohne_freibetraege=steuer_ohne,
        steuervorteil_freibetraege=vorteil,
        kindergeld=kindergeld,
        freibetraege_guenstiger=guenstiger,
        netto_kindervorteil=netto,
        naeherung=naeherung,
    )
