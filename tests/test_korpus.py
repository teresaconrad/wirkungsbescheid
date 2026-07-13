"""Korpus-Tests: jeder generierte Fall ist engine-konsistent; PDFs und Fotos entstehen;
die Vorverarbeitung liest sie wieder ein."""
from decimal import Decimal
from pathlib import Path

import pytest

from app.korpus import FAELLE, generiere
from app.engine import nachrechnen
from app.falllogik import fallmerkmale
from app.models import Bescheid

D = Decimal


@pytest.mark.parametrize("fall", FAELLE, ids=[f.id for f in FAELLE])
def test_fall_engine_konsistent(fall):
    b = generiere(fall)
    erg = nachrechnen(b)
    assert erg.validiert, [f"{a.feld}: {a.extrahiert} vs {a.berechnet}"
                           for a in erg.abweichungen]


def test_matrix_abdeckung():
    """Die 10 Fälle decken alle Merkmale der Fallmatrix ab."""
    abgedeckt: set[str] = set()
    for fall in FAELLE:
        m = fallmerkmale(generiere(fall))
        abgedeckt |= {k for k, v in m.items() if v}
    pflicht = {"zusammenveranlagung", "erstattung", "nachzahlung", "kinder",
               "guenstigerpruefung_kindergeld", "progressionsvorbehalt",
               "dba_auslandseinkuenfte", "kapital_tariflich", "vermietung",
               "selbstaendig_gewerblich", "gewerbesteuer_anrechnung", "renten",
               "faktorverfahren", "verlustabzug", "unterhalt_realsplitting",
               "agb_zumutbare_belastung", "p35a", "soli_faellt_an", "kirchensteuer",
               "vorlaeufigkeit", "vorauszahlungen_kuenftig", "aenderungsbescheid"}
    fehlend = pflicht - abgedeckt
    assert not fehlend, f"Nicht abgedeckte Merkmale: {fehlend}"


def test_k03_kindergeld_guenstiger():
    b = generiere(next(f for f in FAELLE if f.id == "K03"))
    assert b.festsetzung.hinzurechnung_kindergeld is None  # Kindergeld war günstiger
    assert b.festsetzung.zve.wert == b.festsetzung.einkommen.wert  # keine FB im zvE


def test_k04_pv_und_milderungszone():
    b = generiere(next(f for f in FAELLE if f.id == "K04"))
    assert b.festsetzung.steuersatz_besonders is not None
    assert D("0") < b.festsetzung.soli.wert  # fällt an …
    from app.engine import soli_voll
    assert b.festsetzung.soli.wert < soli_voll(b.festsetzung.tarifliche_est.wert)


def test_rendering_und_vorverarbeitung(tmp_path):
    from app.korpus.render_alt import render_pdf
    from app.korpus.foto import pdf_zu_fotos
    from app.extraktion import vorverarbeite

    b = generiere(FAELLE[0])
    pdf = tmp_path / "K01.pdf"
    render_pdf(b, pdf)
    assert pdf.stat().st_size > 2000

    vv = vorverarbeite(pdf)
    assert len(vv.bilder) == 3                    # 3 Seiten
    assert vv.textlayer and "Einkommensteuer" in vv.textlayer
    assert "zu versteuerndes Einkommen" in vv.textlayer

    fotos = pdf_zu_fotos(pdf, tmp_path)
    assert len(fotos) == 3
    vv_foto = vorverarbeite(fotos[0])
    assert len(vv_foto.bilder) == 1 and vv_foto.textlayer is None


def test_golden_json_roundtrip(tmp_path):
    b = generiere(FAELLE[3])
    p = tmp_path / "K04.json"
    p.write_text(b.model_dump_json(), "utf-8")
    b2 = Bescheid.model_validate_json(p.read_text("utf-8"))
    assert nachrechnen(b2).validiert
    assert b2.festsetzung.festgesetzte_est.wert == b.festsetzung.festgesetzte_est.wert
