from decimal import Decimal

from app.engine import grundtarif, soli, ermaessigung_35a, splitting_vorteil
from app.wirkung import ebenen_split, kategorien, kreislauf

D = Decimal


def test_tarif_2024_eckwerte():
    assert grundtarif(D("11784"), 2024) == D("0")          # Grundfreibetrag
    assert grundtarif(D("11785"), 2024) == D("0")          # knapp darüber → < 1 €
    assert grundtarif(D("17005"), 2024) == D("991")        # Zonengrenze 2→3
    assert grundtarif(D("100000"), 2024) == D("31363")     # 0,42x − 10.636,31
    assert grundtarif(D("300000"), 2024) == D("116028")    # 0,45x − 18.971,06


def test_soli_freigrenze():
    assert soli(D("18130"), 2024, splitting=False) == D("0")
    assert soli(D("50000"), 2024, splitting=False) == D("2750.00")  # voller Satz


def test_35a():
    assert ermaessigung_35a(haushaltsnah=D("3000"), handwerker=D("8000")) == D("1800")
    # Kappen: 20 % von 8.000 = 1.600 → max 1.200; 20 % von 3.000 = 600


def test_splitting_vorteil_positiv_bei_ungleichen_einkommen():
    v = splitting_vorteil(D("132730"), anteil_a=D("0.62"), pv_a=D("0"),
                          pv_b=D("13538"), jahr=2024)
    assert v > D("0")


def test_ebenen_split_stadtstaat():
    s = ebenen_split(D("42441"), D("21.53"), "Berlin")
    assert s.stadtstaat
    # 57,5 % der ESt bleiben in Berlin (Doku 09: 24.404 €)
    assert (s.land + s.gemeinde).quantize(D("1")) in (D("24403"), D("24404"))
    assert s.soli_an_bund == D("21.53")


def test_kategorien_fall_k():
    """Eurostat-COFOG 2024 (DE, S13): alle 11 Kategorien verifiziert, Summe exakt 1."""
    kats = {k.id: k for k in kategorien(D("42441"))}
    assert len(kats) == 11
    assert all(k.verifiziert for k in kats.values())
    assert sum(k.anteil for k in kats.values()) == D("1.00000")
    assert kats["soziale_sicherung"].betrag == D("17517.95")   # 41,276 %
    assert kats["zinsen"].betrag == D("977.42")                # 2,303 % (GF0107)
    bafoeg = [e for e in kats["bildung"].einheiten if "BAföG" in e["einheit"]][0]
    assert D("5.8") <= bafoeg["anzahl"] <= D("6.0")            # weiterhin ~5,9 Monate
    assert bafoeg["label"] == "bezogen auf Jahr 2024"


def test_verkehr_unteranteil_und_groessenordnung():
    """Autobahn-Einheit rechnet auf dem isolierten Verkehrsanteil (GF0405) —
    Datenmodell-Regel: Einheiten hängen an COFOG-Gruppen. Größenordnungs-Fit: 0,5–500."""
    kats = {k.id: k for k in kategorien(D("42441"))}
    autobahn = [e for e in kats["wirtschaft_verkehr"].einheiten
                if "Autobahn" in e["einheit"]][0]
    assert D("0.5") < autobahn["anzahl"] < D("500")            # ~5,8 Meter-Jahre
    assert "Verkehr" in autobahn["basis_zusatz"]


def test_zinsen_transparenz_indikator():
    kats = {k.id: k for k in kategorien(D("42441"))}
    assert kats["zinsen"].transparenz
    assert any("Cent je Steuer-Euro" in e["einheit"] for e in kats["zinsen"].einheiten)


def test_deltas_p7():
    from app.wirkung import deltas
    d = deltas(D("42441"))
    assert d["jahr_von"] == 2023 and d["jahr_bis"] == 2024
    zins = next(z for z in d["zeilen"] if "Zinsen" in z["name"])
    assert zins["pflicht"] and zins["steigt"] and zins["prozent"] == "22,4"
    assert len(d["zeilen"]) == 4                               # Zinsen-Pflicht + Top 3


def test_kreislauf():
    k = kreislauf(D("17231.05"), D("6000"))
    assert k["saldo"] == D("11231.05")
