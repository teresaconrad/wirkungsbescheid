"""
SolZG — Solidaritätszuschlag mit Freigrenze und Milderungszone.

Bemessungsgrundlage: ESt unter Berücksichtigung der Kinderfreibeträge
(ohne Kindergeld-Hinzurechnung), § 3 Abs. 2a SolZG.
Milderungszone: höchstens 11,9 % von (BMG − Freigrenze); Kappung bei 5,5 % der BMG.
Validiert am Realfall K: BMG 36.441, Freigrenze 36.260 → 11,9 % × 181 = 21,53 €.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR

D = Decimal

# Freigrenzen (Grundtarif / Splitting)
FREIGRENZEN: dict[int, tuple[Decimal, Decimal]] = {
    2023: (D("17543"), D("35086")),
    2024: (D("18130"), D("36260")),
    2025: (D("19950"), D("39900")),
}

SATZ = D("0.055")
MILDERUNG = D("0.119")


def soli(bmg: Decimal, jahr: int, splitting: bool) -> Decimal:
    """Soli in Euro, auf den Cent abgerundet."""
    bmg = D(bmg)
    if jahr not in FREIGRENZEN:
        raise ValueError(f"Keine Soli-Freigrenze für {jahr} hinterlegt")
    fg = FREIGRENZEN[jahr][1 if splitting else 0]
    if bmg <= fg:
        return D("0")
    betrag = min(SATZ * bmg, MILDERUNG * (bmg - fg))
    return betrag.quantize(D("0.01"), rounding=ROUND_FLOOR)


def soli_voll(bmg: Decimal) -> Decimal:
    """Rechnerischer voller Soli (für die Ersparnis-Erklärzeile)."""
    return (SATZ * D(bmg)).quantize(D("0.01"), rounding=ROUND_FLOOR)
