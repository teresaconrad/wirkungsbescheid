"""
„Ihr Jahr in 5 Zahlen" — die Kontrafaktuale, die das Finanzamt intern ohnehin rechnet.

1. Splitting-Vorteil (Differenz zu zwei Einzelveranlagungen, dokumentierte Näherung)
2. Progressionsvorbehalts-Effekt (Steuer mit PV − Steuer ohne PV)
3. Kindervorteil (aus Günstigerprüfung, kinder.py)
4. Soli-Ersparnis in der Milderungszone
5. Erstattung/Nachzahlung (direkt aus dem Bescheid)
"""
from __future__ import annotations

from decimal import Decimal

from .tarif import grundtarif, splittingtarif
from .progression import steuer_mit_pv
from .soli import soli, soli_voll

D = Decimal


def splitting_vorteil(zve_gemeinsam: Decimal, anteil_a: Decimal,
                      pv_a: Decimal, pv_b: Decimal, jahr: int) -> Decimal:
    """
    Näherung: das gemeinsame zvE wird im Einkünfte-Verhältnis (anteil_a, 0..1) auf beide
    Personen verteilt und je einzeln veranlagt (inkl. je eigenem PV).
    Amtlich exakt wäre die getrennte Zurechnung aller Abzüge — v1-Ausbaustufe;
    die Näherung wird im Bescheid als solche gekennzeichnet (P9).
    """
    zve_gemeinsam = D(zve_gemeinsam)
    zve_a = (zve_gemeinsam * D(anteil_a)).quantize(D("1"))
    zve_b = zve_gemeinsam - zve_a
    steuer_a, _ = steuer_mit_pv(zve_a, D(pv_a), jahr, splitting=False)
    steuer_b, _ = steuer_mit_pv(zve_b, D(pv_b), jahr, splitting=False)
    steuer_zusammen, _ = steuer_mit_pv(zve_gemeinsam, D(pv_a) + D(pv_b), jahr, splitting=True)
    return steuer_a + steuer_b - steuer_zusammen


def pv_effekt(zve: Decimal, pv_einkuenfte: Decimal, jahr: int, splitting: bool) -> Decimal:
    """Mehrsteuer durch den Progressionsvorbehalt (exakt, amtliche Rundung)."""
    mit, _ = steuer_mit_pv(zve, pv_einkuenfte, jahr, splitting)
    ohne = splittingtarif(zve, jahr) if splitting else grundtarif(zve, jahr)
    return mit - ohne


def soli_ersparnis(bmg: Decimal, jahr: int, splitting: bool) -> Decimal:
    """Ersparnis gegenüber dem vollen 5,5-%-Zuschlag (Milderungszone/Freigrenze)."""
    return soli_voll(bmg) - soli(bmg, jahr, splitting)
