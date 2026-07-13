"""
Vorverarbeitung (Stufe 1): PDF/JPEG/PNG/HEIC → Liste normalisierter PNG-Bilder
für die Vision-Extraktion. Born-digital-PDFs liefern zusätzlich den Textlayer.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

MAX_KANTE = 1600  # px — ausreichend für Bescheid-Typografie, spart Tokens


@dataclass
class Vorverarbeitet:
    bilder: list[bytes]          # PNG-Bytes je Seite
    textlayer: str | None = None # nur bei born-digital-PDFs


def _normalisiere(img: Image.Image) -> bytes:
    img = img.convert("RGB")
    if max(img.size) > MAX_KANTE:
        f = MAX_KANTE / max(img.size)
        img = img.resize((int(img.width * f), int(img.height * f)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def vorverarbeite(pfad: Path) -> Vorverarbeitet:
    suffix = pfad.suffix.lower()
    if suffix == ".pdf":
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(pfad))
        bilder = [_normalisiere(p.render(scale=2.2).to_pil()) for p in doc]
        text = "\n\n".join(p.get_textpage().get_text_range() for p in doc).strip()
        return Vorverarbeitet(bilder=bilder, textlayer=text or None)
    if suffix in (".heic", ".heif"):
        import pillow_heif
        pillow_heif.register_heif_opener()
        return Vorverarbeitet(bilder=[_normalisiere(Image.open(pfad))])
    if suffix in (".jpg", ".jpeg", ".png"):
        return Vorverarbeitet(bilder=[_normalisiere(Image.open(pfad))])
    raise ValueError(f"Nicht unterstütztes Format: {suffix} (PDF, JPEG, PNG, HEIC)")
