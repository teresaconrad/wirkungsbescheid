"""
§ 32a EStG — Tarifformel mit amtlichen Rundungsregeln.

Rundung: zvE wird auf vollen Euro abgerundet; der Steuerbetrag wird auf vollen Euro
abgerundet (§ 32a Abs. 1). Splitting (§ 32a Abs. 5): das Zweifache des (bereits
abgerundeten) Steuerbetrags auf die Hälfte des gemeinsamen zvE.
Validiert am Realfall K (VZ 2024): halbes zvE 73.134 → 20.079 € → ×2 = 40.158 €.

Parameter-Status:
- 2024: Fassung nach dem Gesetz zur steuerlichen Freistellung des Existenzminimums
  (Dez. 2024, GFB 11.784) — durch Fall-K-Golden-Test bestätigt. ✅
- 2023: Inflationsausgleichsgesetz. ⏳ gegen BMF-Steuerrechner zu verifizieren
- 2025: Steuerfortentwicklungsgesetz. ⏳ gegen BMF-Steuerrechner zu verifizieren
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR

D = Decimal

TARIFE: dict[int, dict] = {
    2023: {
        "gfb": D("10908"), "e2": D("15999"), "e3": D("62809"), "e4": D("277825"),
        "z2": (D("979.18"), D("1400")),
        "z3": (D("192.59"), D("2397"), D("966.53")),
        "z4": (D("0.42"), D("9972.98")),
        "z5": (D("0.45"), D("18307.73")),
    },
    2024: {
        "gfb": D("11784"), "e2": D("17005"), "e3": D("66760"), "e4": D("277825"),
        "z2": (D("954.80"), D("1400")),
        "z3": (D("181.19"), D("2397"), D("991.21")),
        "z4": (D("0.42"), D("10636.31")),
        "z5": (D("0.45"), D("18971.06")),
    },
    2025: {
        "gfb": D("12096"), "e2": D("17443"), "e3": D("68480"), "e4": D("277825"),
        "z2": (D("932.30"), D("1400")),
        "z3": (D("176.64"), D("2397"), D("1015.13")),
        "z4": (D("0.42"), D("10911.92")),
        "z5": (D("0.45"), D("19246.67")),
    },
}


def _floor_euro(x: Decimal) -> Decimal:
    return x.quantize(D("1"), rounding=ROUND_FLOOR)


def grundtarif(zve: Decimal, jahr: int) -> Decimal:
    """Einkommensteuer nach Grundtarif, auf vollen Euro abgerundet."""
    if jahr not in TARIFE:
        raise ValueError(f"Kein Tarif für {jahr} hinterlegt")
    t = TARIFE[jahr]
    x = _floor_euro(D(zve))
    if x <= t["gfb"]:
        return D("0")
    if x <= t["e2"]:
        a, b = t["z2"]
        y = (x - t["gfb"]) / D("10000")
        est = (a * y + b) * y
    elif x <= t["e3"]:
        a, b, c = t["z3"]
        z = (x - t["e2"]) / D("10000")
        est = (a * z + b) * z + c
    elif x <= t["e4"]:
        a, c = t["z4"]
        est = a * x - c
    else:
        a, c = t["z5"]
        est = a * x - c
    return _floor_euro(est)


def splittingtarif(zve_gemeinsam: Decimal, jahr: int) -> Decimal:
    """§ 32a Abs. 5: 2 × Steuer auf die Hälfte des gemeinsamen zvE."""
    halb = D(zve_gemeinsam) / D("2")
    return grundtarif(halb, jahr) * D("2")


def tarif(zve: Decimal, jahr: int, splitting: bool) -> Decimal:
    return splittingtarif(zve, jahr) if splitting else grundtarif(zve, jahr)
