"""
Web-Shell: Upload → Extraktion → Review → Kombi-Bescheid.

Datenschutz (Blueprint Abschn. 6): keine Persistenz — Bescheide leben nur im
Arbeitsspeicher der Session und werden nie auf Platte geschrieben; sensible IDs
sind schon im Schema nicht vorgesehen.

Start:  uvicorn app.web.main:app --reload
Modi:   mit ANTHROPIC_API_KEY → echte Extraktion; ohne → Demo-Modus (Korpus-Fälle).
"""
from __future__ import annotations

import os
import secrets
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..engine import nachrechnen
from ..models import Bescheid, Betrag, Herkunft, Provenienz
from ..renderer import render_html

app = FastAPI(title="Wirkungsbescheid-Demonstrator")

_env = Environment(loader=FileSystemLoader(Path(__file__).parent),
                   autoescape=select_autoescape(["html", "j2"]))

# In-Memory-Ablage: Token → Bescheid (bewusst keine Datenbank, keine Dateien)
_SITZUNGEN: dict[str, Bescheid] = {}
_MAX_SITZUNGEN = 200

KORPUS_DIR = Path(__file__).resolve().parents[2] / "korpus"

# Felder, die im Review-Screen editierbar sind (Pfad im Modell, Label, Cent-genau)
REVIEW_FELDER = [
    ("festsetzung.zve", "Zu versteuerndes Einkommen", False),
    ("festsetzung.tarifliche_est", "Tarifliche Einkommensteuer", False),
    ("festsetzung.hinzurechnung_kindergeld", "Hinzurechnung Kindergeld", False),
    ("festsetzung.festgesetzte_est", "Festgesetzte Einkommensteuer", False),
    ("festsetzung.soli", "Solidaritätszuschlag", True),
    ("festsetzung.kirchensteuer", "Kirchensteuer", True),
    ("festsetzung.einkommen", "Einkommen", False),
    ("festsetzung.kinderfreibetraege_summe", "Kinderfreibeträge (Summe)", False),
    ("abrechnung.erstattung", "Erstattung", True),
    ("abrechnung.nachzahlung", "Nachzahlung", True),
]


def _merke(b: Bescheid) -> str:
    if len(_SITZUNGEN) >= _MAX_SITZUNGEN:
        _SITZUNGEN.pop(next(iter(_SITZUNGEN)))
    token = secrets.token_urlsafe(12)
    _SITZUNGEN[token] = b
    return token


def _hole(token: str) -> Bescheid:
    if token not in _SITZUNGEN:
        raise HTTPException(404, "Sitzung abgelaufen — bitte erneut hochladen.")
    return _SITZUNGEN[token]


def _feld(b: Bescheid, pfad: str):
    obj = b
    for teil in pfad.split("."):
        obj = getattr(obj, teil)
        if obj is None:
            return None
    return obj


def _setze(b: Bescheid, pfad: str, wert: Decimal | None):
    *eltern, letzter = pfad.split(".")
    obj = b
    for teil in eltern:
        obj = getattr(obj, teil)
    if wert is None:
        setattr(obj, letzter, None)
    else:
        setattr(obj, letzter, Betrag(wert=wert, provenienz=Provenienz(
            herkunft=Herkunft.nutzerkorrigiert)))


@app.get("/", response_class=HTMLResponse)
def start():
    from ..korpus.faelle import FAELLE
    vorhanden = {p.stem for p in KORPUS_DIR.glob("K*.json")} \
        if KORPUS_DIR.exists() else set()
    demo_faelle = [{"id": f.id, "beschreibung": f.beschreibung or f.titel,
                    "ort": f.finanzamt.removeprefix("Finanzamt ").strip()}
                   for f in FAELLE if f.id in vorhanden]
    return _env.get_template("upload.html.j2").render(
        api_verfuegbar=bool(os.environ.get("ANTHROPIC_API_KEY")),
        demo_faelle=demo_faelle)


def _fehlerseite(meldung: str, status: int = 422) -> HTMLResponse:
    return HTMLResponse(_env.get_template("fehler.html.j2").render(
        meldung=meldung), status_code=status)


@app.post("/upload")
async def upload(datei: list[UploadFile] = File(...)):
    dateien = datei  # Formularfeld heißt „datei"; Mehrfachauswahl liefert Liste
    if len(dateien) == 1 and (dateien[0].filename or "").lower().endswith(".json"):
        b = Bescheid.model_validate_json(
            (await dateien[0].read()).decode("utf-8"))  # Golden-JSON (Demo/Test)
        return RedirectResponse(f"/review/{_merke(b)}", status_code=303)
    suffixe = [Path(d.filename or "upload").suffix.lower() for d in dateien]
    erlaubt = (".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif")
    if any(s not in erlaubt for s in suffixe):
        return _fehlerseite("Bitte PDF, JPEG, PNG oder HEIC hochladen — "
                            "bei Fotos gerne mehrere auf einmal (eine je Seite).", 415)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _fehlerseite("Extraktion nicht konfiguriert (kein API-Key). "
                            "Nutzen Sie den Demo-Modus.", 503)
    from ..extraktion import vorverarbeite_dateien
    from ..extraktion.client import extrahiere, ExtraktionsFehler
    # temporäre Dateien nur für die Vorverarbeitung; sofort wieder gelöscht
    tmp_pfade: list[Path] = []
    try:
        for d, suffix in zip(dateien, suffixe):
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(await d.read())
                tmp_pfade.append(Path(tmp.name))
        try:
            vv = vorverarbeite_dateien(tmp_pfade)
        except ValueError as e:
            return _fehlerseite(str(e))
        except Exception:
            return _fehlerseite("Die Datei konnte nicht gelesen werden — sie ist "
                                "möglicherweise beschädigt. Bitte erneut scannen "
                                "oder fotografieren.")
    finally:
        for p in tmp_pfade:
            p.unlink(missing_ok=True)
    try:
        erg = extrahiere(vv)
    except ExtraktionsFehler as e:
        return _fehlerseite(str(e))
    except Exception:
        import logging, traceback
        logging.getLogger("uvicorn.error").error(
            "Extraktion fehlgeschlagen:\n%s", traceback.format_exc())
        return _fehlerseite("Beim Auslesen ist ein unerwarteter Fehler aufgetreten. "
                            "Bitte erneut versuchen; Details stehen im Server-Log.",
                            500)
    return RedirectResponse(f"/review/{_merke(erg.bescheid)}", status_code=303)


@app.get("/demo/{fall_id}")
def demo(fall_id: str):
    pfad = KORPUS_DIR / f"{fall_id}.json"
    if not pfad.exists():
        raise HTTPException(404, "Demo-Fall nicht gefunden.")
    b = Bescheid.model_validate_json(pfad.read_text("utf-8"))
    return RedirectResponse(f"/review/{_merke(b)}", status_code=303)


@app.get("/review/{token}", response_class=HTMLResponse)
def review(token: str):
    b = _hole(token)
    nr = nachrechnen(b)
    abweichend = {a.feld for a in nr.abweichungen}
    felder = []
    for pfad, label, cents in REVIEW_FELDER:
        wert = _feld(b, pfad)
        if wert is None:
            continue
        w = wert.wert if hasattr(wert, "wert") else wert
        konf = wert.provenienz.konfidenz if hasattr(wert, "provenienz") else 1.0
        felder.append({"pfad": pfad, "label": label,
                       "wert": f"{w:.2f}" if cents else f"{w:.0f}",
                       "unsicher": konf < 0.9,
                       "abweichend": pfad.split(".")[-1] in abweichend})
    return _env.get_template("review.html.j2").render(
        token=token, felder=felder, nr=nr, b=b,
        abweichungen=[{"feld": a.feld, "extrahiert": str(a.extrahiert),
                       "berechnet": str(a.berechnet)} for a in nr.abweichungen])


@app.post("/korrektur/{token}")
async def korrektur(token: str, pfad: str = Form(...), wert: str = Form(...)):
    b = _hole(token)
    try:
        dez = Decimal(wert.replace(".", "").replace(",", ".")) if wert.strip() else None
    except InvalidOperation:
        raise HTTPException(422, f"Kein gültiger Betrag: {wert}")
    if pfad not in {p for p, _, _ in REVIEW_FELDER}:
        raise HTTPException(422, "Unbekanntes Feld.")
    _setze(b, pfad, dez)
    return RedirectResponse(f"/review/{token}", status_code=303)


@app.get("/bescheid/{token}", response_class=HTMLResponse)
def bescheid(token: str):
    return render_html(_hole(token))


@app.post("/schliessen/{token}")
def schliessen(token: str):
    _SITZUNGEN.pop(token, None)  # Daten sofort verwerfen
    return RedirectResponse("/", status_code=303)
