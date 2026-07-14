"""
Extraktions-Client (Stufe 2+3): Claude-Vision → Schema → Nachrechnungs-Schleife.

Ablauf:
1. Bilder + ggf. Textlayer an die API, Antwort gegen das Pydantic-Schema geparst.
2. nachrechnen(): Stimmen tarifliche ESt / Steuersatz / festgesetzte ESt / Soli auf
   den Euro, gilt die Extraktion als validiert.
3. Bei Abweichungen: EIN gezielter Korrektur-Durchlauf mit benannten Feldern.
4. Bleiben Abweichungen: Ergebnis mit validiert=False zurück → Review-Screen
   (Nutzerin korrigiert; nie stilles Raten).

Benötigt ANTHROPIC_API_KEY (im Cloud-Deployment als Secret).
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass

from ..engine import nachrechnen, Nachrechnung
from ..models import Bescheid
from .preprocess import Vorverarbeitet
from .prompt import SYSTEM, user_prompt

MODELL = os.environ.get("EXTRAKTION_MODELL", "claude-sonnet-5")


@dataclass
class Extraktionsergebnis:
    bescheid: Bescheid
    nachrechnung: Nachrechnung
    durchlaeufe: int

    @property
    def validiert(self) -> bool:
        return self.nachrechnung.validiert


class ExtraktionsFehler(Exception):
    """Extraktion fehlgeschlagen — Meldung ist nutzertauglich formuliert."""


def _parse(antwort: str) -> Bescheid:
    text = antwort.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    # Robust gegen erklärenden Text vor/nach dem JSON: äußerstes Objekt isolieren.
    if not text.startswith("{"):
        anfang, ende = text.find("{"), text.rfind("}")
        if anfang == -1 or ende == -1:
            raise ExtraktionsFehler(
                "Das Dokument konnte nicht als Steuerbescheid gelesen werden. "
                "Bitte prüfen Sie, ob alle Seiten lesbar fotografiert sind.")
        text = text[anfang:ende + 1]
    try:
        return Bescheid.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValueError) as e:
        raise ExtraktionsFehler(
            "Die ausgelesenen Daten waren unvollständig oder fehlerhaft. "
            "Häufigste Ursache: Es fehlen Seiten des Bescheids. Bitte alle "
            "Seiten hochladen (mehrere Fotos gleichzeitig auswählbar).") from e


def _api_aufruf(client, vv: Vorverarbeitet, korrekturhinweis: str | None) -> Bescheid:
    content: list[dict] = [
        {"type": "image",
         "source": {"type": "base64", "media_type": "image/png",
                    "data": base64.b64encode(b).decode()}}
        for b in vv.bilder
    ]
    content.append({"type": "text",
                    "text": user_prompt(vv.textlayer, korrekturhinweis)})
    resp = client.messages.create(
        model=MODELL, max_tokens=8000, system=SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    return _parse(resp.content[0].text)


def extrahiere(vv: Vorverarbeitet, api_key: str | None = None) -> Extraktionsergebnis:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"],
                                 timeout=180.0, max_retries=2)

    try:
        bescheid = _api_aufruf(client, vv, None)
    except anthropic.APIStatusError as e:
        raise ExtraktionsFehler(
            f"Der Auslese-Dienst hat einen Fehler gemeldet (HTTP {e.status_code}). "
            "Bitte in einer Minute erneut versuchen.") from e
    except anthropic.APIConnectionError as e:
        raise ExtraktionsFehler(
            "Der Auslese-Dienst ist gerade nicht erreichbar. "
            "Bitte in einer Minute erneut versuchen.") from e
    erg = nachrechnen(bescheid)
    durchlaeufe = 1

    if not erg.validiert:
        hinweis = "\n".join(
            f"- Feld '{a.feld}': extrahiert {a.extrahiert}, nachgerechnet {a.berechnet}"
            for a in erg.abweichungen)
        try:
            bescheid2 = _api_aufruf(client, vv, hinweis)
            erg2 = nachrechnen(bescheid2)
            durchlaeufe = 2
            if erg2.validiert or len(erg2.abweichungen) < len(erg.abweichungen):
                bescheid, erg = bescheid2, erg2
        except Exception:
            pass  # Korrektur-Durchlauf gescheitert → Erstergebnis + Review-Screen

    return Extraktionsergebnis(bescheid=bescheid, nachrechnung=erg,
                               durchlaeufe=durchlaeufe)
