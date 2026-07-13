"""Kombi-Bescheid rendern: python3 -m app.renderer <bescheid.json> [ziel.html]"""
import sys
from pathlib import Path

from ..models import Bescheid
from . import render_html

quelle = Path(sys.argv[1])
ziel = Path(sys.argv[2]) if len(sys.argv) > 2 else quelle.with_suffix(".wirkbescheid.html")
b = Bescheid.model_validate_json(quelle.read_text("utf-8"))
ziel.write_text(render_html(b), "utf-8")
print(f"→ {ziel}")
