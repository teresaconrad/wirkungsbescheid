"""
Wirkungsbescheid — Kanonisches Bescheid-Schema (Vertrag zwischen Extraktion, Engine, Renderer).

Prinzipien:
- Sensible Identifikatoren (Steuer-ID, IdNr., IBAN) sind NICHT Teil des Schemas (Datenschutz-Regel 2).
- Jedes extrahierte Feld kann eine Provenienz tragen (Konfidenz, Seite, Quelle).
- Beträge in Euro als Decimal-kompatible Strings/Floats; die Engine rechnet mit Decimal.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Veranlagungsart(str, Enum):
    einzel = "einzel"
    zusammen = "zusammen"  # Splitting


class Bescheidart(str, Enum):
    erstbescheid = "erstbescheid"
    aenderungsbescheid = "aenderungsbescheid"


class Herkunft(str, Enum):
    extrahiert = "extrahiert"
    berechnet = "berechnet"
    nutzerkorrigiert = "nutzerkorrigiert"


class Provenienz(BaseModel):
    konfidenz: float = Field(1.0, ge=0.0, le=1.0)
    seite: Optional[int] = None
    herkunft: Herkunft = Herkunft.extrahiert


class Betrag(BaseModel):
    """Euro-Betrag mit Provenienz."""
    wert: Decimal
    provenienz: Provenienz = Provenienz()

    @classmethod
    def von(cls, wert, **kw) -> "Betrag":
        return cls(wert=Decimal(str(wert)), provenienz=Provenienz(**kw))


class Meta(BaseModel):
    finanzamt: Optional[str] = None
    veranlagungsjahr: int
    bescheiddatum: Optional[str] = None
    bescheidart: Bescheidart = Bescheidart.erstbescheid
    vorlaeufigkeitsvermerke: list[str] = []  # § 165 AO, Kurzbezeichnungen
    bundesland: Optional[str] = None  # für Ebenen-Split / Stadtstaaten


class Kind(BaseModel):
    freibetrag: Optional[Betrag] = None       # angesetzter Freibetrag (inkl. BEA)
    kindergeld_verrechnet: Optional[Betrag] = None
    auswaertig_ausbildung: bool = False


class EinkuenftePerson(BaseModel):
    """Einkünfte je Person. Bei Einzelveranlagung nur Person A."""
    bruttolohn: Optional[Betrag] = None
    werbungskosten: Optional[Betrag] = None
    einkuenfte_nsa: Optional[Betrag] = None          # nichtselbständige Arbeit
    kapital_tariflich: Optional[Betrag] = None        # § 32d Abs. 6 / Ausnahmen
    kapital_abgeltend: Optional[Betrag] = None
    vermietung_verpachtung: Optional[Betrag] = None
    selbstaendig: Optional[Betrag] = None             # § 18
    gewerbebetrieb: Optional[Betrag] = None           # § 15
    gewerbesteuer_messbetrag: Optional[Betrag] = None # für § 35
    renten_besteuerungsanteil: Optional[Betrag] = None
    sonstige: Optional[Betrag] = None
    lohnersatzleistungen: Optional[Betrag] = None     # Progressionsvorbehalt § 32b
    auslaendische_einkuenfte_dba: Optional[Betrag] = None  # DBA-Progressionsvorbehalt
    lohnsteuer_einbehalten: Optional[Betrag] = None
    faktorverfahren: bool = False


class Abzuege(BaseModel):
    vorsorgeaufwendungen: Optional[Betrag] = None
    sonderausgaben_uebrige: Optional[Betrag] = None
    spenden: Optional[Betrag] = None
    kinderbetreuung: Optional[Betrag] = None
    unterhalt_realsplitting: Optional[Betrag] = None  # § 10 Abs. 1a Nr. 1
    agb_geltend_gemacht: Optional[Betrag] = None      # außergewöhnl. Belastungen (z. B. Krankheit)
    agb_zumutbare_belastung: Optional[Betrag] = None
    agb_abziehbar: Optional[Betrag] = None
    ausbildungsfreibetrag: Optional[Betrag] = None
    verlustabzug: Optional[Betrag] = None             # § 10d Vor-/Rücktrag
    p35a_haushaltsnah: Optional[Betrag] = None        # Aufwendungen (nicht Ermäßigung)
    p35a_handwerker: Optional[Betrag] = None


class Festsetzung(BaseModel):
    gesamtbetrag_einkuenfte: Optional[Betrag] = None
    einkommen: Optional[Betrag] = None
    kinderfreibetraege_summe: Optional[Betrag] = None
    zve: Optional[Betrag] = None
    steuersatz_besonders: Optional[Decimal] = None    # § 32b, Prozent mit 4 Nachkommastellen
    tarifliche_est: Optional[Betrag] = None
    hinzurechnung_kindergeld: Optional[Betrag] = None # § 31 S. 4
    ermaessigung_35a: Optional[Betrag] = None
    ermaessigung_35: Optional[Betrag] = None          # Gewerbesteuer-Anrechnung
    festgesetzte_est: Optional[Betrag] = None
    soli: Optional[Betrag] = None
    kirchensteuer: Optional[Betrag] = None


class Abrechnung(BaseModel):
    lohnsteuer_gesamt: Optional[Betrag] = None
    kapitalertragsteuer: Optional[Betrag] = None
    vorauszahlungen_geleistet: Optional[Betrag] = None
    bereits_getilgt: Optional[Betrag] = None
    erstattung: Optional[Betrag] = None               # positiv = Erstattung
    nachzahlung: Optional[Betrag] = None
    vorauszahlungen_kuenftig_quartal: Optional[Betrag] = None
    lastschrift: Optional[bool] = None


class Bescheid(BaseModel):
    """Wurzelobjekt: ein vollständig extrahierter Einkommensteuerbescheid."""
    meta: Meta
    veranlagungsart: Veranlagungsart
    kirchensteuerpflicht: bool = False
    kinder: list[Kind] = []
    person_a: EinkuenftePerson
    person_b: Optional[EinkuenftePerson] = None
    abzuege: Abzuege = Abzuege()
    festsetzung: Festsetzung = Festsetzung()
    abrechnung: Abrechnung = Abrechnung()

    def anzahl_kinder(self) -> int:
        return len(self.kinder)

    def lohnersatz_gesamt(self) -> Decimal:
        s = Decimal("0")
        for p in [self.person_a, self.person_b]:
            if p is not None:
                if p.lohnersatzleistungen:
                    s += p.lohnersatzleistungen.wert
                if p.auslaendische_einkuenfte_dba:
                    s += p.auslaendische_einkuenfte_dba.wert
        return s
