# Wirkungsbescheid-Demonstrator — Cloud-Deployment (z. B. Railway/Fly.io)
# Secrets zur Laufzeit: ANTHROPIC_API_KEY (Extraktion); ohne Key läuft der Demo-Modus.
FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
# Demo-Testkorpus (K01–K10) wird beim Build aus den Falldefinitionen erzeugt —
# muss deshalb nicht im Repo liegen.
RUN python3 -m app.korpus korpus

# Keine Persistenz: kein Volume, keine Datenbank — Sitzungen leben im RAM.
EXPOSE 8000
CMD ["uvicorn", "app.web.main:app", "--host", "0.0.0.0", "--port", "8000"]
