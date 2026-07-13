"""
Foto-Degradierung: macht aus einer PDF-Seite ein realistisches „Handyfoto"
(Schräglage, ungleichmäßige Helligkeit, Rauschen, JPEG-Artefakte) — Robustheits-Input
für den Extraktions-Layer.
"""
from __future__ import annotations

import random
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageEnhance, ImageFilter


def pdf_zu_fotos(pdf_pfad: Path, ziel_dir: Path, seed: int = 7) -> list[Path]:
    rnd = random.Random(seed)
    doc = pdfium.PdfDocument(str(pdf_pfad))
    ergebnisse = []
    for i, page in enumerate(doc):
        img = page.render(scale=2.2).to_pil().convert("RGB")
        # Schräglage
        img = img.rotate(rnd.uniform(-2.5, 2.5), expand=True, fillcolor=(120, 110, 100))
        # ungleichmäßige Helligkeit + leichter Farbstich
        img = ImageEnhance.Brightness(img).enhance(rnd.uniform(0.82, 1.05))
        img = ImageEnhance.Contrast(img).enhance(rnd.uniform(0.85, 1.0))
        img = ImageEnhance.Color(img).enhance(1.15)
        # leichte Unschärfe + Rauschen über JPEG-Kompression
        img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
        ziel = ziel_dir / f"{pdf_pfad.stem}_foto_s{i + 1}.jpg"
        img.save(ziel, "JPEG", quality=rnd.randint(55, 70))
        ergebnisse.append(ziel)
    return ergebnisse
