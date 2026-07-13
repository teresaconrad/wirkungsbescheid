"""End-to-End-Durchstich (Schritt 3): kompletter Ablauf über die Web-Shell,
Extraktion durch Golden-JSONs ersetzt (Mock) — beweist die Pipeline ohne API-Key."""
import pytest
from fastapi.testclient import TestClient

from app.web.main import app, KORPUS_DIR

client = TestClient(app)
ALLE = sorted(p.stem for p in KORPUS_DIR.glob("K*.json"))


def test_startseite():
    r = client.get("/")
    assert r.status_code == 200
    assert "Wirkungsbescheid" in r.text and "Demo-Modus" in r.text


@pytest.mark.parametrize("fall_id", ALLE)
def test_e2e_demo_bis_bescheid(fall_id):
    r = client.get(f"/demo/{fall_id}", follow_redirects=False)
    assert r.status_code == 303
    token = r.headers["location"].split("/")[-1]

    r = client.get(f"/review/{token}")
    assert r.status_code == 200
    assert "Nachrechnung stimmt überein" in r.text  # alle Korpus-Fälle validieren

    r = client.get(f"/bescheid/{token}")
    assert r.status_code == 200
    assert "Beitrag zum Gemeinwesen" in r.text and "Seite 6 von 6" in r.text


def test_e2e_upload_json():
    pfad = KORPUS_DIR / "K04.json"
    r = client.post("/upload", files={"datei": ("K04.json", pfad.read_bytes(),
                                                "application/json")},
                    follow_redirects=False)
    assert r.status_code == 303


def test_e2e_korrektur_schleife():
    """Nutzerin korrigiert einen (absichtlich verfälschten) Wert → Validierung kippt und heilt."""
    token = client.get("/demo/K01", follow_redirects=False).headers["location"].split("/")[-1]
    korrekt = "6746"
    # verfälschen
    r = client.post(f"/korrektur/{token}", data={"pfad": "festsetzung.festgesetzte_est",
                                                 "wert": "6000"}, follow_redirects=False)
    assert r.status_code == 303
    assert "Nachrechnung weicht ab" in client.get(f"/review/{token}").text
    # heilen
    client.post(f"/korrektur/{token}", data={"pfad": "festsetzung.festgesetzte_est",
                                             "wert": korrekt})
    assert "Nachrechnung stimmt überein" in client.get(f"/review/{token}").text


def test_sitzung_beenden_verwirft_daten():
    token = client.get("/demo/K01", follow_redirects=False).headers["location"].split("/")[-1]
    client.post(f"/schliessen/{token}")
    assert client.get(f"/review/{token}").status_code == 404
