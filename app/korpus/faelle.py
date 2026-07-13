"""
Testkorpus-Falldefinitionen: 10 Fälle über die volle Fallmatrix (v1 inkl. Ex-v2).
Nur Eingangsgrößen — alle Steuerketten rechnet der Generator engine-konsistent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

D = Decimal
KFB_JE_KIND_2024 = D("9540")  # Kinderfreibetrag 6.612 + BEA 2.928 (Paar, VZ 2024)


@dataclass
class PersonDef:
    brutto: Decimal = D("0")
    wk: Decimal = D("0")
    kapital_tariflich: Decimal = D("0")
    vuv: Decimal = D("0")
    selbstaendig: Decimal = D("0")
    gewerbebetrieb: Decimal = D("0")
    gewst_messbetrag: Decimal = D("0")
    renten: Decimal = D("0")
    lohnersatz: Decimal = D("0")           # § 32b (Elterngeld, ALG I, KUG …)
    dba_auslandseinkuenfte: Decimal = D("0")
    lohnsteuer: Decimal = D("0")
    faktorverfahren: bool = False


@dataclass
class FallDef:
    id: str
    titel: str
    jahr: int = 2024
    zusammen: bool = False
    bundesland: str = "Berlin"
    kirchensteuer: bool = False
    kinder: int = 0
    kindergeld_erhalten: Decimal = D("0")
    person_a: PersonDef = field(default_factory=PersonDef)
    person_b: Optional[PersonDef] = None
    vorsorge: Decimal = D("0")
    spenden: Decimal = D("0")
    kinderbetreuung: Decimal = D("0")
    unterhalt_realsplitting: Decimal = D("0")
    agb_geltend: Decimal = D("0")
    ausbildungsfreibetrag: Decimal = D("0")
    verlustabzug: Decimal = D("0")
    p35a_haushaltsnah: Decimal = D("0")
    p35a_handwerker: Decimal = D("0")
    vz_geleistet: Decimal = D("0")
    aenderungsbescheid: bool = False
    vorlaeufigkeit: list[str] = field(default_factory=list)


FAELLE: list[FallDef] = [
    FallDef(id="K01", titel="Einzel, einfach, Erstattung",
            person_a=PersonDef(brutto=D("48000"), wk=D("1800"), lohnsteuer=D("7900")),
            vorsorge=D("8200"), spenden=D("240")),

    FallDef(id="K02", titel="Einzel, Kapital tariflich (§ 32d Abs. 6), Nachzahlung",
            person_a=PersonDef(brutto=D("39000"), wk=D("1230"),
                               kapital_tariflich=D("3100"), lohnsteuer=D("5100")),
            vorsorge=D("6900")),

    FallDef(id="K03", titel="Zusammen, 2 Kinder, Kindergeld günstiger",
            zusammen=True, kinder=2, kindergeld_erhalten=D("6000"),
            person_a=PersonDef(brutto=D("46000"), wk=D("1230"), lohnsteuer=D("3800")),
            person_b=PersonDef(brutto=D("18000"), wk=D("1230"), lohnsteuer=D("300")),
            vorsorge=D("11000"), kinderbetreuung=D("1600")),

    FallDef(id="K04", titel="Zusammen, 3 Kinder, Elterngeld-PV, Soli-Milderungszone",
            zusammen=True, kinder=3, kindergeld_erhalten=D("7500"),
            person_a=PersonDef(brutto=D("124000"), wk=D("1400"), lohnsteuer=D("33000")),
            person_b=PersonDef(brutto=D("72000"), wk=D("2900"),
                               lohnersatz=D("12400"), lohnsteuer=D("15500")),
            vorsorge=D("20800"), spenden=D("900"), agb_geltend=D("3400"),
            vorlaeufigkeit=["Grundfreibetrag", "Kinderfreibeträge"]),

    FallDef(id="K05", titel="Einzel, Rente (Besteuerungsanteil), Soli 0",
            person_a=PersonDef(renten=D("16800"), lohnsteuer=D("0")),
            vorsorge=D("2900"), vz_geleistet=D("400")),

    FallDef(id="K06", titel="Zusammen, selbständig + gewerblich, § 35, Nachzahlung",
            zusammen=True, kirchensteuer=True,
            person_a=PersonDef(selbstaendig=D("71000")),
            person_b=PersonDef(gewerbebetrieb=D("38000"), gewst_messbetrag=D("980")),
            vorsorge=D("14500"), vz_geleistet=D("12000")),

    FallDef(id="K07", titel="Einzel, V+V, Verlustvortrag § 10d, § 35a Handwerker",
            person_a=PersonDef(brutto=D("58000"), wk=D("2200"), vuv=D("9400"),
                               lohnsteuer=D("10900")),
            vorsorge=D("9600"), verlustabzug=D("6500"), p35a_handwerker=D("4200")),

    FallDef(id="K08", titel="Zusammen, DBA-PV, Kirchensteuer, Faktorverfahren",
            zusammen=True, kirchensteuer=True, bundesland="Nordrhein-Westfalen",
            person_a=PersonDef(brutto=D("67000"), wk=D("1500"),
                               dba_auslandseinkuenfte=D("14800"),
                               lohnsteuer=D("11200"), faktorverfahren=True),
            person_b=PersonDef(brutto=D("41000"), wk=D("1230"),
                               lohnsteuer=D("5400"), faktorverfahren=True),
            vorsorge=D("15800")),

    FallDef(id="K09", titel="Einzel, ALG-I-PV, Krankheitskosten/zumutbare Belastung",
            person_a=PersonDef(brutto=D("31000"), wk=D("1230"),
                               lohnersatz=D("8200"), lohnsteuer=D("3600")),
            vorsorge=D("5900"), agb_geltend=D("2800"),
            vorlaeufigkeit=["Grundfreibetrag"]),

    FallDef(id="K10", titel="Änderungsbescheid, Zusammen, Realsplitting",
            zusammen=True, aenderungsbescheid=True,
            person_a=PersonDef(brutto=D("83000"), wk=D("3100"), lohnsteuer=D("15400")),
            person_b=PersonDef(brutto=D("29000"), wk=D("1230"), lohnsteuer=D("2100")),
            vorsorge=D("13900"), unterhalt_realsplitting=D("9000"),
            p35a_haushaltsnah=D("2400")),
]
