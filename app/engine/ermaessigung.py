"""
Steuerermäßigungen: § 35a (haushaltsnahe Dienstleistungen/Handwerker) und
§ 35 (Gewerbesteuer-Anrechnung, vereinfacht).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR

D = Decimal

P35A_SATZ = D("0.20")
P35A_MAX_HAUSHALTSNAH = D("4000")
P35A_MAX_HANDWERKER = D("1200")
P35_FAKTOR = D("4")  # § 35: 4-faches des Gewerbesteuer-Messbetrags (seit VZ 2020)


def ermaessigung_35a(haushaltsnah: Decimal = D("0"),
                     handwerker: Decimal = D("0")) -> Decimal:
    e = min(P35A_SATZ * D(haushaltsnah), P35A_MAX_HAUSHALTSNAH)
    e += min(P35A_SATZ * D(handwerker), P35A_MAX_HANDWERKER)
    return e.quantize(D("1"), rounding=ROUND_FLOOR)


def ermaessigung_35(messbetrag: Decimal, tarifliche_est_anteilig: Decimal) -> Decimal:
    """Vereinfacht: 4 × Messbetrag, gekappt auf die anteilige tarifliche ESt.
    (Die tatsächlich gezahlte GewSt als zweite Kappung ist v1-Ausbaustufe.)"""
    return min(P35_FAKTOR * D(messbetrag), D(tarifliche_est_anteilig)) \
        .quantize(D("1"), rounding=ROUND_FLOOR)
