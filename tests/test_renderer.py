"""Renderer-Tests: alle 10 Korpus-Fälle rendern fehlerfrei; Kernzahlen und
konditionale Bausteine (P16) erscheinen fallabhängig."""
import pytest

from app.korpus import FAELLE, generiere
from app.renderer import render_html


@pytest.mark.parametrize("fall", FAELLE, ids=[f.id for f in FAELLE])
def test_rendert_fehlerfrei(fall):
    b = generiere(fall)
    html = render_html(b)
    assert "Beitrag zum Gemeinwesen" in html
    assert "Seite 6 von 6" in html
    # festgesetzte Steuer erscheint irgendwo im Dokument
    ganze = f"{b.festsetzung.festgesetzte_est.wert:,.0f}".replace(",", ".")
    assert ganze in html


def _html(fall_id: str) -> str:
    return render_html(generiere(next(f for f in FAELLE if f.id == fall_id)))


def test_p16_erstattung_vs_nachzahlung():
    h_erst, h_nach = _html("K01"), _html("K06")
    assert "Ihre Erstattung" in h_erst and "Ihre Nachzahlung" not in h_erst
    assert "Säumniszuschläge" not in h_erst          # Zahlungsfolgen nur im Nachzahlungsfall
    assert "Ihre Nachzahlung" in h_nach and "Säumniszuschläge" in h_nach


def test_p16_pv_box_nur_bei_pv():
    assert "Progressionsvorbehalt" in _html("K04")
    assert "Progressionsvorbehalt" not in _html("K01")


def test_p16_guenstigerpruefung_beide_ausgaenge():
    assert "verrechnet" in _html("K04")              # Freibeträge günstiger
    assert "Es bleibt also beim Kindergeld" in _html("K03")


def test_kist_baustein():
    h = _html("K08")
    assert "Konfessionsgemeinschaft" in h
    assert "keine Verfügung über diese Mittel" in h


def test_stadtstaat_vs_flaechenland():
    assert "Stadtstaat" in _html("K01")              # Berlin
    assert "Ihre Gemeinde" in _html("K08")           # NRW: Drei-Balken-Split


def test_soli_gleitzone_box():
    h = _html("K04")
    assert "Gleitzone" in h and "kein Fehler, sondern Ihr Schutz" in h


def test_einheiten_mit_bezugsjahr():
    h = _html("K04")
    assert "BAföG-Monat" in h and "bezogen auf Jahr 2024" in h
    assert "Kindergeld-Monat" in h and "bezogen auf Jahr 2026" in h
