"""
Rendert einen Bescheid im BISLANG GÄNGIGEN Format (Behörden-Layout) als PDF —
Input-Material für den Extraktions-Test. Bewusst spröde: Blocksatz-Prosa,
Paragrafenketten, keine Erklärungen.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from ..models import Bescheid, Veranlagungsart, Bescheidart

W, H = A4
LM, RM, TM, BM = 55, 55, 60, 55


def fmt(x, cents=False) -> str:
    if x is None:
        return ""
    d = Decimal(str(x.wert if hasattr(x, "wert") else x))
    s = f"{d:,.2f}" if cents or d != d.to_integral_value() else f"{d:,.0f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


class Writer:
    def __init__(self, c: Canvas):
        self.c, self.y = c, H - TM

    def brk(self, need=14):
        if self.y - need < BM:
            self.c.showPage()
            self.y = H - TM

    def line(self, text="", font="Helvetica", size=9, x=LM, dy=13):
        self.brk(dy)
        self.c.setFont(font, size)
        self.c.drawString(x, self.y, text)
        self.y -= dy

    def kv(self, label, value, x2=W - RM, font="Helvetica", size=9, dy=13):
        self.brk(dy)
        self.c.setFont(font, size)
        self.c.drawString(LM, self.y, label)
        self.c.drawRightString(x2, self.y, value)
        self.y -= dy

    def kv3(self, label, va, vb, dy=13):
        """Zweispaltig (Ehemann/Ehefrau)."""
        self.brk(dy)
        self.c.setFont("Helvetica", 9)
        self.c.drawString(LM, self.y, label)
        self.c.drawRightString(LM + 330, self.y, va)
        self.c.drawRightString(W - RM, self.y, vb)
        self.y -= dy

    def gap(self, n=7):
        self.y -= n


def render_pdf(b: Bescheid, pfad: Path, name_a="Alex Muster", name_b="Kim Muster"):
    c = Canvas(str(pfad), pagesize=A4)
    w = Writer(c)
    zusammen = b.veranlagungsart == Veranlagungsart.zusammen
    f, ab = b.festsetzung, b.abrechnung
    jahr = b.meta.veranlagungsjahr

    # ---- Seite 1: Kopf, Festsetzung, Abrechnung
    w.line(b.meta.finanzamt or "Finanzamt", "Helvetica-Bold", 10)
    w.line("Steuernummer 12/345/67890 · IdNr. XX XXX XXX XXX")
    w.line(f"Bescheiddatum: {b.meta.bescheiddatum}")
    w.gap()
    w.line(f"{name_a}" + (f" und {name_b}" if zusammen else ""))
    w.line("Musterweg 1, 10000 Musterstadt")
    w.gap(14)
    titel = f"Bescheid für {jahr} über Einkommensteuer und Solidaritätszuschlag"
    if b.kirchensteuerpflicht:
        titel += " und Kirchensteuer"
    if b.meta.bescheidart == Bescheidart.aenderungsbescheid:
        titel += " (Änderungsbescheid nach § 172 AO)"
    w.line(titel, "Helvetica-Bold", 11, dy=16)
    if b.meta.vorlaeufigkeitsvermerke:
        w.line("Der Bescheid ist nach § 165 Abs. 1 Satz 2 AO teilweise vorläufig hinsichtlich:")
        for v in b.meta.vorlaeufigkeitsvermerke:
            w.line(f"  - {v}")
    w.gap(10)
    w.line("Festsetzung", "Helvetica-Bold", 10, dy=15)
    w.kv("Einkommensteuer", fmt(f.festgesetzte_est) + " EUR")
    w.kv("Solidaritätszuschlag", fmt(f.soli, cents=True) + " EUR")
    if f.kirchensteuer is not None:
        w.kv("Kirchensteuer", fmt(f.kirchensteuer, cents=True) + " EUR")
    w.gap(10)
    w.line("Abrechnung", "Helvetica-Bold", 10, dy=15)
    if ab.lohnsteuer_gesamt:
        w.kv("ab Steuerabzug vom Lohn", fmt(ab.lohnsteuer_gesamt) + " EUR")
    if ab.vorauszahlungen_geleistet:
        w.kv("ab festgesetzte Vorauszahlungen", fmt(ab.vorauszahlungen_geleistet) + " EUR")
    if ab.erstattung:
        w.kv("Überzahlung insgesamt", fmt(ab.erstattung, cents=True) + " EUR", font="Helvetica-Bold")
        w.line("Der Erstattungsbetrag wird auf das benannte Konto überwiesen. IBAN DExx xxxx xxxx")
    if ab.nachzahlung:
        w.kv("Verbleibende Beträge (bitte zahlen Sie spätestens bis 18.06.2026)",
             fmt(ab.nachzahlung, cents=True) + " EUR", font="Helvetica-Bold")
        w.line("Bei verspäteter Zahlung entstehen Säumniszuschläge (§ 240 AO).")
    if ab.vorauszahlungen_kuenftig_quartal:
        w.gap(6)
        w.line("Vorauszahlungen ab 2026 (§ 37 EStG):")
        w.kv("  je 10.03. / 10.06. / 10.09. / 10.12.",
             fmt(ab.vorauszahlungen_kuenftig_quartal) + " EUR")

    # ---- Seite 2: Besteuerungsgrundlagen
    c.showPage(); w.y = H - TM
    w.line("Besteuerungsgrundlagen", "Helvetica-Bold", 11, dy=16)
    pers = [(name_a, b.person_a)] + ([(name_b, b.person_b)] if b.person_b else [])
    if zusammen:
        w.kv3("", name_a, name_b or "")
    for label, attr, cents in [
        ("Bruttoarbeitslohn", "bruttolohn", False),
        ("ab Werbungskosten", "werbungskosten", False),
        ("Einkünfte aus nichtselbständiger Arbeit", "einkuenfte_nsa", False),
        ("Einkünfte aus Kapitalvermögen, die der tariflichen ESt unterliegen", "kapital_tariflich", False),
        ("Einkünfte aus Vermietung und Verpachtung", "vermietung_verpachtung", False),
        ("Einkünfte aus selbständiger Arbeit", "selbstaendig", False),
        ("Einkünfte aus Gewerbebetrieb", "gewerbebetrieb", False),
        ("Renten (Besteuerungsanteil)", "renten_besteuerungsanteil", False),
    ]:
        vals = [getattr(p, attr) for _, p in pers]
        if not any(vals):
            continue
        if zusammen:
            w.kv3(label, fmt(vals[0]) if vals[0] else "-",
                  fmt(vals[1]) if len(vals) > 1 and vals[1] else "-")
        else:
            w.kv(label, fmt(vals[0]) + " EUR")
    w.gap()
    w.kv("Gesamtbetrag der Einkünfte", fmt(f.gesamtbetrag_einkuenfte) + " EUR", font="Helvetica-Bold")
    a = b.abzuege
    for label, val in [
        ("ab beschränkt abziehbare Vorsorgeaufwendungen", a.vorsorgeaufwendungen),
        ("ab Zuwendungen nach § 10b EStG", a.spenden),
        ("ab Kinderbetreuungskosten (§ 10 Abs. 1 Nr. 5 EStG)", a.kinderbetreuung),
        ("ab Unterhaltsleistungen (§ 10 Abs. 1a Nr. 1 EStG)", a.unterhalt_realsplitting),
        ("ab Verlustabzug nach § 10d EStG", a.verlustabzug),
        ("ab Freibetrag zur Abgeltung eines Sonderbedarfs (§ 33a Abs. 2 EStG)", a.ausbildungsfreibetrag),
    ]:
        if val:
            w.kv(label, fmt(val) + " EUR")
    if a.agb_geltend_gemacht:
        w.kv("Außergewöhnliche Belastungen: geltend gemacht", fmt(a.agb_geltend_gemacht) + " EUR")
        w.kv("  ab zumutbare Belastung", fmt(a.agb_zumutbare_belastung) + " EUR")
        w.kv("  abziehbar", fmt(a.agb_abziehbar) + " EUR")
    w.kv("Einkommen", fmt(f.einkommen) + " EUR", font="Helvetica-Bold")
    if f.kinderfreibetraege_summe and f.hinzurechnung_kindergeld:
        w.kv(f"ab Freibeträge für Kinder ({len(b.kinder)} Kinder)",
             fmt(f.kinderfreibetraege_summe) + " EUR")
    w.kv("zu versteuerndes Einkommen", fmt(f.zve) + " EUR", font="Helvetica-Bold")
    w.gap(10)
    w.line("Berechnung der Steuer", "Helvetica-Bold", 10, dy=15)
    tarifname = "Splittingtarif" if zusammen else "Grundtarif"
    if f.steuersatz_besonders is not None:
        satz = fmt(f.steuersatz_besonders, cents=False)
        w.line(f"zu versteuern nach dem {tarifname} mit Progressionsvorbehalt "
               f"(Steuersatz {str(f.steuersatz_besonders).replace('.', ',')} %)")
    else:
        w.line(f"zu versteuern nach dem {tarifname}")
    w.kv("tarifliche Einkommensteuer", fmt(f.tarifliche_est) + " EUR")
    if f.hinzurechnung_kindergeld:
        w.kv("dazu Anspruch auf Kindergeld", fmt(f.hinzurechnung_kindergeld) + " EUR")
    if f.ermaessigung_35a:
        w.kv("ab Ermäßigung nach § 35a EStG", fmt(f.ermaessigung_35a) + " EUR")
    if f.ermaessigung_35:
        w.kv("ab Ermäßigung nach § 35 EStG", fmt(f.ermaessigung_35) + " EUR")
    w.kv("festzusetzende Einkommensteuer", fmt(f.festgesetzte_est) + " EUR", font="Helvetica-Bold")

    # ---- Seite 3: Erläuterungen (Textbaustein-Kaskade, absichtlich juristisch)
    c.showPage(); w.y = H - TM
    w.line("Erläuterungen", "Helvetica-Bold", 11, dy=16)
    pv_summe = b.lohnersatz_gesamt()
    if pv_summe:
        w.line(f"Bei der Berechnung des Steuersatzes wurden Lohn-/Entgeltersatzleistungen bzw.")
        w.line(f"nach DBA steuerfreie Einkünfte in Höhe von {fmt(pv_summe)} EUR gemäß § 32b EStG")
        w.line("berücksichtigt (Progressionsvorbehalt).")
        w.gap()
    if f.hinzurechnung_kindergeld:
        w.line("Die Prüfung nach § 31 EStG hat ergeben, dass der Abzug der Freibeträge für")
        w.line("Kinder günstiger ist als der Anspruch auf Kindergeld. Der Anspruch auf")
        w.line("Kindergeld wurde der tariflichen Einkommensteuer hinzugerechnet.")
        w.gap()
    elif b.kinder:
        w.line("Die Prüfung nach § 31 EStG hat ergeben, dass das Kindergeld günstiger ist als")
        w.line("der Abzug der Freibeträge für Kinder. Freibeträge wurden nicht angesetzt;")
        w.line("bei Solidaritätszuschlag und Kirchensteuer wurden sie berücksichtigt (§ 51a EStG).")
        w.gap()
    if any(p.faktorverfahren for _, p in pers):
        w.line("Der Lohnsteuerabzug erfolgte im Faktorverfahren (§ 39f EStG).")
        w.gap()
    if b.meta.vorlaeufigkeitsvermerke:
        w.line("Die Festsetzung ist teilweise vorläufig (§ 165 Abs. 1 Satz 2 AO). Die")
        w.line("Vorläufigkeit umfasst die im Bescheidkopf bezeichneten Punkte und erfolgt im")
        w.line("Hinblick auf anhängige Verfahren vor dem BVerfG bzw. BFH. Ein Einspruch ist")
        w.line("insoweit nicht erforderlich.")
        w.gap()
    w.line("Belege sind nach § 147 AO, § 147a AO, § 14b UStG, § 50 EStDV aufzubewahren.")
    w.gap()
    w.line("Rechtsbehelfsbelehrung", "Helvetica-Bold", 10, dy=15)
    w.line("Gegen diesen Bescheid kann innerhalb eines Monats nach Bekanntgabe Einspruch")
    w.line("eingelegt werden (§ 355 AO). Der Einspruch ist bei dem oben bezeichneten")
    w.line("Finanzamt schriftlich einzureichen oder zur Niederschrift zu erklären.")
    c.save()
