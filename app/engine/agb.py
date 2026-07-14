"""
§ 33 Abs. 3 EStG — zumutbare Belastung, stufenweise Berechnung (BFH VI R 75/14).

Validiert am Realfall K: GdE 176.363, zusammen, 3 Kinder → 3.015 € (abgerundet).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR

D = Decimal

STUFE1 = D("15340")
STUFE2 = D("51130")

# Prozentsätze (Stufe1, Stufe2, darüber) je Konstellation
def _saetze(splitting: bool, kinder: int) -> tuple[Decimal, Decimal, Decimal]:
    if kinder >= 3:
        return D("0.01"), D("0.01"), D("0.02")
    if kinder >= 1:
        return D("0.02"), D("0.03"), D("0.04")
    if splitting:
        return D("0.04"), D("0.05"), D("0.06")
    return D("0.05"), D("0.06"), D("0.07")


def zumutbare_belastung(gde: Decimal, splitting: bool, kinder: int) -> Decimal:
    """Stufenweise: jeder GdE-Teilbetrag mit seinem Satz. Ergebnis auf vollen Euro abgerundet."""
    gde = D(gde)
    s1, s2, s3 = _saetze(splitting, kinder)
    betrag = D("0")
    betrag += min(gde, STUFE1) * s1
    if gde > STUFE1:
        betrag += (min(gde, STUFE2) - STUFE1) * s2
    if gde > STUFE2:
        betrag += (gde - STUFE2) * s3
    return betrag.quantize(D("1"), rounding=ROUND_FLOOR)
