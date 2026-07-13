"""
Wirkungsmodell (Stufe 6): Ebenen-Split → Kategorien → Einheiten → Kreislauf.

Entscheidungen 13.07.2026:
- Basis = festgesetzte ESt + Soli. ESt: Art.-106-Split (42,5/42,5/15, Stadtstaaten 57,5 % lokal);
  Soli: 100 % Bund.
- Kirchensteuer: kein Wirkungsmodell, eigener Ausweis-Baustein (siehe datenpaket.json).
- Indikatoren: aktuellste verifizierte Werte, je Wert mit „bezogen auf Jahr X".
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

D = Decimal
_DATEN = json.loads((Path(__file__).parent / "datenpaket.json").read_text("utf-8"))


@dataclass
class EbenenSplit:
    bund: Decimal
    land: Decimal
    gemeinde: Decimal
    stadtstaat: bool
    lokal_gesamt: Decimal  # Land+Gemeinde bei Stadtstaaten, sonst Gemeinde
    soli_an_bund: Decimal


@dataclass
class Kategorie:
    id: str
    name: str
    betrag: Decimal
    anteil: Decimal
    verifiziert: bool
    quelle: str
    einheiten: list[dict] = field(default_factory=list)
    hinweis: str | None = None
    transparenz: bool = False


def _r2(x: Decimal) -> Decimal:
    return x.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def ebenen_split(est: Decimal, soli: Decimal, bundesland: str | None) -> EbenenSplit:
    e = _DATEN["ebenen_split"]
    est = D(est)
    bund = _r2(est * D(str(e["bund"]))) + D(str(soli))
    land = _r2(est * D(str(e["land"])))
    gemeinde = _r2(est * D(str(e["gemeinde"])))
    stadtstaat = bundesland in e["stadtstaaten"]
    lokal = land + gemeinde if stadtstaat else gemeinde
    return EbenenSplit(bund=bund, land=land, gemeinde=gemeinde,
                       stadtstaat=stadtstaat, lokal_gesamt=lokal,
                       soli_an_bund=D(str(soli)))


def kategorien(gesamtbetrag: Decimal) -> list[Kategorie]:
    """Gesamtstaats-Mix proportional (UK-Logik), Eurostat-COFOG 2024.
    Einheiten mit "basis"-Feld rechnen auf dem Unteranteil (z. B. Verkehr aus GF0405),
    gemäß Datenmodell-Regel: Einheiten hängen an COFOG-Gruppen, nie an heterogenen
    Divisionen."""
    gesamtbetrag = D(gesamtbetrag)
    kosten = _DATEN["einheitskosten"]
    result = []
    for k in _DATEN["kategorien_gesamtstaat"]:
        betrag = _r2(gesamtbetrag * D(str(k["anteil"])))
        kat = Kategorie(id=k["id"], name=k["name"], betrag=betrag,
                        anteil=D(str(k["anteil"])), verifiziert=k["verifiziert"],
                        quelle=k["quelle"], hinweis=k.get("hinweis"),
                        transparenz=k.get("transparenz", False))
        for e in kosten:
            if e["kategorie"] != k["id"]:
                continue
            if "basis" in e:
                unter = k["unteranteile"][e["basis"]]
                basis_betrag = _r2(gesamtbetrag * D(str(unter["anteil"])))
                zusatz = f'davon {e["basis"].capitalize()}-Anteil {euro_fmt(basis_betrag)}'
            else:
                basis_betrag, zusatz = betrag, None
            kat.einheiten.append({
                "einheit": e["einheit"],
                "anzahl": (basis_betrag / D(str(e["kostensatz"]))).quantize(D("0.1")),
                "bezugsjahr": e["bezugsjahr"],
                "label": f"bezogen auf Jahr {e['bezugsjahr']}",
                "quelle": e["quelle"],
                "basis_zusatz": zusatz,
            })
        if kat.transparenz:
            cent = (kat.anteil * 100).quantize(D("0.1"))
            kat.einheiten.append({
                "einheit": f"{str(cent).replace('.', ',')} Cent je Steuer-Euro",
                "anzahl": None, "bezugsjahr": _DATEN["deltas"]["jahr_bis"],
                "label": f"bezogen auf Jahr {_DATEN['deltas']['jahr_bis']}",
                "quelle": kat.quelle, "basis_zusatz": None,
            })
        result.append(kat)
    return result


def euro_fmt(x: Decimal) -> str:
    s = f"{x:,.0f}".replace(",", ".")
    return s + " €"


def deltas(gesamtbetrag: Decimal) -> dict:
    """Vorjahres-Deltas (P7): Zinsen-Pflichtzeile + Top-3, übersetzt auf den
    individuellen Beitrag (Anteil des Nutzers an der Kategorie, beide Jahre)."""
    d = _DATEN["deltas"]
    gesamtbetrag = D(gesamtbetrag)
    gesamt_total = D(str(d["gesamt"]["bis"]))
    zeilen = []
    for z in d["zeilen"]:
        anteil_bis = D(str(z["bis"])) / gesamt_total
        ihr_bis = _r2(gesamtbetrag * anteil_bis)
        zeilen.append({"name": z["name"], "prozent": str(z["prozent"]).replace(".", ","),
                       "steigt": z["prozent"] > 0, "ihr_betrag": ihr_bis,
                       "pflicht": z.get("pflicht", False)})
    return {"jahr_von": d["jahr_von"], "jahr_bis": d["jahr_bis"],
            "gesamt_prozent": str(d["gesamt"]["prozent"]).replace(".", ","),
            "zeilen": zeilen}


def kreislauf(beitrag_soziales: Decimal, kindergeld_erhalten: Decimal) -> dict:
    """„Was Sie einzahlen — und was zurückfließt" (nur aus Bescheiddaten)."""
    return {
        "eingezahlt_soziales": D(beitrag_soziales),
        "zurueckgeflossen_kindergeld": D(kindergeld_erhalten),
        "saldo": D(beitrag_soziales) - D(kindergeld_erhalten),
    }


def kirchensteuer_baustein() -> str:
    return _DATEN["kirchensteuer"]["baustein"]
