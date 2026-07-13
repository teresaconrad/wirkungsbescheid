"""
§ 32b EStG — Progressionsvorbehalt (Lohnersatzleistungen, DBA-steuerfreie Einkünfte).

Besonderer Steuersatz = Tarifsteuer auf (zvE + PV-Einkünfte) / (zvE + PV-Einkünfte),
als Prozentsatz auf vier Nachkommastellen ABGESCHNITTEN (nicht gerundet).
Validiert am Realfall K: 40.158 / 146.268 = 27,45508 % → 27,4550 % → Steuer 36.441 €.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR

from .tarif import tarif, _floor_euro

D = Decimal


def besonderer_steuersatz(zve: Decimal, pv_einkuenfte: Decimal, jahr: int,
                          splitting: bool) -> Decimal:
    """Prozentsatz, vier Nachkommastellen, abgeschnitten. 0, wenn keine PV-Einkünfte."""
    zve = _floor_euro(D(zve))
    pv = D(pv_einkuenfte)
    basis = zve + pv
    if pv == 0 or basis <= 0:
        return D("0")
    steuer_basis = tarif(basis, jahr, splitting)
    satz = steuer_basis / basis * D("100")
    return satz.quantize(D("0.0001"), rounding=ROUND_FLOOR)


def steuer_mit_pv(zve: Decimal, pv_einkuenfte: Decimal, jahr: int,
                  splitting: bool) -> tuple[Decimal, Decimal]:
    """(tarifliche ESt, besonderer Steuersatz in %). Ohne PV: normaler Tarif, Satz 0."""
    zve = _floor_euro(D(zve))
    if D(pv_einkuenfte) == 0:
        return tarif(zve, jahr, splitting), D("0")
    satz = besonderer_steuersatz(zve, pv_einkuenfte, jahr, splitting)
    steuer = _floor_euro(satz / D("100") * zve)
    return steuer, satz
