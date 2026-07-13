"""Renderer (Stufe 7): Bescheid → Kombi-Steuer-und-Wirkungsbescheid (HTML)."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models import Bescheid
from .kontext import baue_kontext

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent),
    autoescape=select_autoescape(["html", "j2"]),
)


def render_html(b: Bescheid) -> str:
    return _env.get_template("template.html.j2").render(**baue_kontext(b))
