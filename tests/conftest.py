"""Testvorbereitung: Der Demo-Korpus (K01–K10) liegt nicht im Repo — er wird
aus den Falldefinitionen erzeugt (wie im Docker-Build). Fehlt er, baut diese
Fixture ihn einmalig vor dem Testlauf."""
from pathlib import Path

KORPUS = Path(__file__).resolve().parents[1] / "korpus"


def pytest_configure(config):
    if not any(KORPUS.glob("K*.json")):
        from app.korpus.__main__ import main
        main(KORPUS)
