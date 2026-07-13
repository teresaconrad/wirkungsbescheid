"""Korpus bauen: python3 -m app.korpus [zielordner] — erzeugt PDF + Golden-JSON je Fall,
Foto-Varianten für K01 und K04."""
from __future__ import annotations

import sys
from pathlib import Path

from .faelle import FAELLE
from .generator import generiere
from .render_alt import render_pdf
from .foto import pdf_zu_fotos
from ..engine import nachrechnen

FOTO_FAELLE = {"K01", "K04"}


def main(ziel: Path):
    ziel.mkdir(parents=True, exist_ok=True)
    for f in FAELLE:
        b = generiere(f)
        erg = nachrechnen(b)
        status = "OK " if erg.validiert else "ABW"
        (ziel / f"{f.id}.json").write_text(b.model_dump_json(indent=2), "utf-8")
        render_pdf(b, ziel / f"{f.id}.pdf")
        if f.id in FOTO_FAELLE:
            pdf_zu_fotos(ziel / f"{f.id}.pdf", ziel)
        print(f"[{status}] {f.id} {f.titel} — festgesetzt "
              f"{b.festsetzung.festgesetzte_est.wert} €, Soli {b.festsetzung.soli.wert} €")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("korpus"))
