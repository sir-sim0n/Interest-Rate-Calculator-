"""Where every input and output lives in the Excel workbook.

This file is the bridge between the workbook and Python. It is used by

* ``tools/extract_excel_reference.py`` - reads Excel's own saved values;
* ``tools/build_excel_scenarios.py``  - writes new inputs into a copy of the
  workbook and lets LibreOffice recalculate it;
* ``validation/excel_parity.py``      - runs the same inputs through Python.

Each module has ``inputs`` (Python parameter -> cell) and ``outputs``
(Python output name -> cell). Scenarios are plain dictionaries of Python
parameters; ``to_cells`` turns one into the cell values to write.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

from calculator.common import RateType, Timing
from calculator.single_investment import Outcome

WORKBOOK_NAME = "INTEREST-RATE-CALCULATOR-48581275.xlsx"

# ---------------------------------------------------------------------------
# Excel's dropdown strings (identical in all five converter grids)
# ---------------------------------------------------------------------------

RATE_ORDER = [RateType.EFFECTIVE_ANNUAL, RateType.EFFECTIVE_PERIODIC, RateType.NOMINAL,
              RateType.SIMPLE, RateType.CONTINUOUS]
CONVERTER_FROM_TEXT = dict(zip(RATE_ORDER, ["effective annual", "effective periodic", "nominal",
                                            "simple", "continous"]))
CONVERTER_TO_TEXT = dict(zip(RATE_ORDER, ["Effective annual", "Effective periodic", "Nominal",
                                          "Simple", "continous"]))

# '2. SINGLE INVESTMENTS' K13 / K14 must equal BACKROOM1!L23:P23 / K24:K28 exactly
SI_OUTCOME_TEXT = {
    Outcome.FUTURE_VALUE: "FUTURE VALUE",
    Outcome.PRESENT_VALUE: "PRESENT VALUE ",
    Outcome.YEARS: "YEARS",
    Outcome.INTEREST_RATE: "INTEREST",
    Outcome.INTEREST_EARNED: "INTEREST EARNED",
}
SI_TYPE_TEXT = {
    RateType.SIMPLE: "SIMPLE ",
    RateType.EFFECTIVE_PERIODIC: "EFFECTIVE PERIODIC",
    RateType.EFFECTIVE_ANNUAL: "EFFECTIVE ANNUAL",
    RateType.NOMINAL: "NOMINAL ",
    RateType.CONTINUOUS: "CONTINOUS",
}


def _norm(text: str) -> str:
    """Excel text comparison ignores case; we also ignore stray spaces."""
    return str(text).strip().lower()


def rate_type_from_excel(text: str) -> RateType:
    for rate_type, label in CONVERTER_FROM_TEXT.items():
        if _norm(label) == _norm(text):
            return rate_type
    raise ValueError(f"Unknown rate type text {text!r}")


def outcome_from_excel(text: str) -> Outcome:
    for outcome, label in SI_OUTCOME_TEXT.items():
        if _norm(label) == _norm(text):
            return outcome
    raise ValueError(f"Unknown outcome text {text!r}")


# ---------------------------------------------------------------------------
# Module definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Module:
    name: str
    sheet: str
    inputs: dict[str, str]            # python parameter -> cell ("Sheet!A1" or "A1" on `sheet`)
    outputs: dict[str, str]           # python output    -> cell
    enum_inputs: dict[str, str] = field(default_factory=dict)  # param -> kind of Excel text

    def cell(self, ref: str) -> tuple[str, str]:
        """Split a cell reference into (sheet, address)."""
        if "!" in ref:
            sheet, address = ref.split("!")
            return sheet.strip("'"), address
        return self.sheet, ref

    def to_cells(self, params: dict) -> dict[tuple[str, str], object]:
        """Cell values to write for a scenario."""
        cells = {}
        for param, ref in self.inputs.items():
            value = params[param]
            kind = self.enum_inputs.get(param)
            if kind == "converter_from":
                value = CONVERTER_FROM_TEXT[RateType(value)]
            elif kind == "converter_to":
                value = CONVERTER_TO_TEXT[RateType(value)]
            elif kind == "si_outcome":
                value = SI_OUTCOME_TEXT[Outcome(value)]
            elif kind == "si_type":
                value = SI_TYPE_TEXT[RateType(value)]
            cells[self.cell(ref)] = value
        return cells

    def params_from_cells(self, get) -> dict:
        """Read a scenario's parameters back from a workbook (``get(sheet, addr)``)."""
        params = {}
        for param, ref in self.inputs.items():
            value = get(*self.cell(ref))
            kind = self.enum_inputs.get(param)
            if kind in ("converter_from", "converter_to"):
                value = rate_type_from_excel(value).value
            elif kind == "si_outcome":
                value = outcome_from_excel(value).value
            elif kind == "si_type":
                value = rate_type_from_excel(value).value  # same words as the converter lists
            params[param] = value
        return params


def _converter(grid: int, sheet: str, cells: list[str], output: str) -> Module:
    names = ["value", "from_periods", "from_type", "from_years", "to_periods", "to_type", "to_years"]
    return Module(
        name=f"rate_converter_grid{grid}",
        sheet=sheet,
        inputs=dict(zip(names, cells)),
        outputs={"converted_rate": output},
        enum_inputs={"from_type": "converter_from", "to_type": "converter_to"},
    )


# The five copies of the converter. On sheets 3 and 4 the "to" period is a
# formula linked to the annuity/loan frequency (L14 = Q10, J14 = R15), so the
# scenario writes to the source cell.
CONVERTERS = {
    1: _converter(1, "1. RATE CONVERTER", ["P11", "P12", "P13", "P14", "R12", "R13", "R14"], "O17"),
    2: _converter(2, "2. SINGLE INVESTMENTS", ["C14", "C15", "C16", "C17", "E15", "E16", "E17"], "E19"),
    3: _converter(3, "3. ANNUITIES", ["J13", "J14", "J15", "J16", "Q10", "L15", "L16"], "L17"),
    4: _converter(4, "4.LOANS", ["H13", "H14", "H15", "H16", "R15", "J15", "J16"], "J17"),
    5: _converter(5, "5. INCREASING ANNUITIES", ["E36", "E37", "E38", "E39", "G37", "G38", "G39"], "G41"),
}

SINGLE_INVESTMENT = Module(
    name="single_investment",
    sheet="2. SINGLE INVESTMENTS",
    inputs={"fv": "K6", "pv": "K7", "rate": "K8", "years": "K9", "periods_per_year": "K10",
            "outcome": "K13", "interest_type": "K14"},
    outputs={"answer": "K16", "years_out": "K17", "rate_out": "K18"},
    enum_inputs={"outcome": "si_outcome", "interest_type": "si_type"},
)

ANNUITIES = Module(
    name="annuities",
    sheet="3. ANNUITIES",
    inputs={"installment": "Q7", "rate": "Q8", "years": "Q9", "periods_per_year": "Q10",
            "pv": "Q11", "fv": "Q12"},
    outputs={
        **{f"arrears.{k}": c for k, c in zip(
            ["future_value", "present_value", "years_from_fv", "years_from_pv",
             "installment_from_fv", "installment_from_pv", "rate_from_fv", "rate_from_pv"],
            ["P24", "P25", "P26", "P27", "P28", "P29", "P30", "P31"])},
        **{f"advance.{k}": c for k, c in zip(
            ["future_value", "present_value", "years_from_fv", "years_from_pv",
             "installment_from_fv", "installment_from_pv", "rate_from_fv", "rate_from_pv"],
            ["R24", "R25", "R26", "R27", "R28", "R29", "R30", "R31"])},
    },
)

LOANS = Module(
    name="loans",
    sheet="4.LOANS",
    inputs={"principal": "R11", "installment": "R12", "years": "R13", "rate": "R14",
            "periods_per_year": "R15", "year_T": "R16"},
    outputs={
        "arrears.installment": "P27", "arrears.loan_amount": "P28", "arrears.balance_at_T": "P29",
        "arrears.interest_next_payment": "P30", "arrears.capital_next_payment": "P31",
        "arrears.payments_needed": "P32", "arrears.last_payment": "P33",
        "arrears.capital_in_year_T": "P34", "arrears.interest_in_year_T": "P35",
        "arrears.total_interest": "P36", "arrears.balance_at_T_plus_1": "P37",
        "advance.installment": "U27", "advance.loan_amount": "U28", "advance.balance_at_T": "U29",
        "advance.interest_next_payment": "U30", "advance.capital_next_payment": "U31",
        "advance.payments_needed": "U32", "advance.last_payment": "U33",
        "advance.total_interest": "U36",
    },
)

INCREASING = Module(
    name="increasing_annuities",
    sheet="5. INCREASING ANNUITIES",
    inputs={"rate": "I8", "payment": "I9", "years": "I10", "periods_per_year": "I11",
            "k": "I12", "m": "I13", "growth": "I14", "pv": "I15", "fv": "I16"},
    outputs={
        **{f"stepped.{t}.{k}": f"{col}{row}" for t, col in (("arrears", "E"), ("advance", "G"))
           for k, row in (("installment_from_fv", 23), ("installment_from_pv", 24),
                          ("future_value", 25), ("present_value", 26))},
        **{f"geometric.{t}.{k}": f"{col}{row}" for t, col in (("arrears", "K"), ("advance", "M"))
           for k, row in (("installment_from_fv", 23), ("installment_from_pv", 24),
                          ("future_value", 25), ("present_value", 26))},
    },
)

RETIREMENT = Module(
    name="retirement",
    sheet="5. INCREASING ANNUITIES",
    inputs={"lump_sum": "J36", "rate": "J37", "inflation": "J38", "lump_sum_periods_per_year": "J39",
            "lump_sum_years": "J40", "contribution_k": "J41", "contribution_m": "J42",
            "first_withdrawal_today": "K36", "years_to_inflate": "K40", "withdrawal_k": "K41",
            "withdrawal_m": "K42"},
    outputs={"first_withdrawal": "N36", "withdrawals_fv": "N37", "withdrawals_pv": "N38",
             "lump_sum_fv": "N39", "first_contribution": "N40"},
)

COUNTRY_RETURN_CELLS = {  # BACKROOM2_TEB!A28:C35 (Excel country names)
    "SouthAfrica": "BACKROOM2_TEB!C28", "Germany": "BACKROOM2_TEB!C29", "USA": "BACKROOM2_TEB!C30",
    "Japan": "BACKROOM2_TEB!C31", "Russia": "BACKROOM2_TEB!C32", "Brazil": "BACKROOM2_TEB!C33",
    "China": "BACKROOM2_TEB!C34", "UK": "BACKROOM2_TEB!C35",
}

BROKER = Module(
    name="broker",
    sheet="TEB",
    inputs={"exchange": "G5", "exchange_company": "H5", "exchange_price": "I5", "exchange_shares": "I7",
            "country": "G15", "country_company": "H15", "country_price": "I15", "country_shares": "I17",
            "years": "I25", "usd_zar": "BACKROOM2_TEB!B23",
            **{f"return.{c}": ref for c, ref in COUNTRY_RETURN_CELLS.items()}},
    outputs={"exchange_cost_usd": "I8", "exchange_cost_zar": "I9", "country_cost_usd": "I18",
             "country_cost_zar": "I19", "projected_value": "I26"},
)

MODULES = [*CONVERTERS.values(), SINGLE_INVESTMENT, ANNUITIES, LOANS, INCREASING, RETIREMENT, BROKER]
MODULES_BY_NAME = {m.name: m for m in MODULES}


# ---------------------------------------------------------------------------
# Extra scenarios recalculated by LibreOffice (tools/build_excel_scenarios.py)
# ---------------------------------------------------------------------------

CONVERTER_PARAM_SETS = {
    "A": dict(value=0.08, from_periods=4, to_periods=12, from_years=1, to_years=1),
    "B": dict(value=0.05, from_periods=12, to_periods=2, from_years=1, to_years=1),
    "C": dict(value=0.06, from_periods=1, to_periods=1, from_years=1, to_years=1),
    "D": dict(value=0.07, from_periods=2, to_periods=4, from_years=6, to_years=3),
}

SI_PARAM_SETS = {
    "S1": dict(fv=10000, pv=2000, rate=0.10, years=10, periods_per_year=8),
    "S2": dict(fv=50000, pv=20000, rate=0.02, years=5, periods_per_year=12),
    "S3": dict(fv=15000, pv=12000, rate=0.07, years=1, periods_per_year=1),
}

ANNUITY_SCENARIOS = {
    "A2": dict(installment=1000, rate=0.01, years=10, periods_per_year=12, pv=50000, fv=200000),
    "A3": dict(installment=2500, rate=0.03, years=3, periods_per_year=4, pv=25000, fv=40000),
    "A4": dict(installment=800, rate=0.005, years=20, periods_per_year=12, pv=100000, fv=400000),
    "A5": dict(installment=10000, rate=0.08, years=15, periods_per_year=1, pv=80000, fv=300000),
    "A6": dict(installment=100, rate=0.02, years=5, periods_per_year=12, pv=10000, fv=7000),
}

LOAN_SCENARIOS = {
    "L2": dict(principal=250000, installment=8500, years=6, rate=0.005, periods_per_year=12, year_T=4),
    "L3": dict(principal=1000000, installment=9000, years=20, rate=0.0085, periods_per_year=12, year_T=5),
    "L4": dict(principal=150000, installment=12000, years=5, rate=0.025, periods_per_year=4, year_T=3),
    "L5": dict(principal=500000, installment=60000, years=10, rate=0.10, periods_per_year=1, year_T=6),
    "L6": dict(principal=80000, installment=2000, years=4, rate=0.01, periods_per_year=12, year_T=2),
    "L7": dict(principal=100000, installment=10300, years=10, rate=0.10, periods_per_year=1, year_T=3),
}

INCREASING_SCENARIOS = {
    "I2": dict(rate=0.01, payment=5000, years=5, periods_per_year=12, k=12, m=5, growth=0.005,
               pv=250000, fv=500000),
    "I3": dict(rate=0.08, payment=20000, years=20, periods_per_year=1, k=1, m=20, growth=0.03,
               pv=300000, fv=1500000),
    "I4": dict(rate=0.015, payment=3000, years=8, periods_per_year=4, k=4, m=8, growth=0.06,
               pv=120000, fv=200000),
}

RETIREMENT_SCENARIOS = {
    "R2": dict(lump_sum=50000, rate=0.006, inflation=0.05, lump_sum_periods_per_year=12, lump_sum_years=30,
               contribution_k=12, contribution_m=30, first_withdrawal_today=10000, years_to_inflate=30,
               withdrawal_k=12, withdrawal_m=25),
    "R3": dict(lump_sum=0, rate=0.08, inflation=0.04, lump_sum_periods_per_year=1, lump_sum_years=25,
               contribution_k=1, contribution_m=25, first_withdrawal_today=200000, years_to_inflate=25,
               withdrawal_k=1, withdrawal_m=20),
}

_MID_BAND = {"SouthAfrica": 0.225, "Germany": 0.21, "USA": 0.085, "Japan": 0.215, "Russia": 0.01,
             "Brazil": 0.175, "China": 0.125, "UK": 0.13}

BROKER_SCENARIOS = {
    "T2": dict(exchange="JSE", exchange_company="MTN Group", exchange_shares=100,
               country="SouthAfrica", country_company="Sasol", country_shares=50,
               years=10, usd_zar=18.5, **{f"return.{c}": r for c, r in _MID_BAND.items()}),
    "T3": dict(exchange="Nasdaq", exchange_company="Apple", exchange_shares=7,
               country="China", country_company="Industrial&CommercialBankofChina", country_shares=3,
               years=3, usd_zar=17.2, **{f"return.{c}": r * 0.9 for c, r in _MID_BAND.items()}),
}


def scenario_list() -> list[dict]:
    """All LibreOffice scenarios: ``{id, module, params, file_group}``.

    Scenarios sharing a ``file_group`` are written into the same workbook copy
    (the five converter grids live on different sheets and do not interact).
    """
    out = []
    for (set_id, base), (f, t) in product(CONVERTER_PARAM_SETS.items(), product(RATE_ORDER, RATE_ORDER)):
        group = f"conv-{set_id}-{RATE_ORDER.index(f)}{RATE_ORDER.index(t)}"
        for grid, module in CONVERTERS.items():
            out.append(dict(id=f"{module.name}/{set_id}/{f.name}->{t.name}", module=module.name,
                            params={**base, "from_type": f.value, "to_type": t.value}, file_group=group))
    for (set_id, base), outcome, rtype in product(SI_PARAM_SETS.items(), Outcome, RATE_ORDER):
        sid = f"single_investment/{set_id}/{outcome.name}/{rtype.name}"
        out.append(dict(id=sid, module="single_investment", file_group=sid,
                        params={**base, "outcome": outcome.value, "interest_type": rtype.value}))
    for module, table in (("annuities", ANNUITY_SCENARIOS), ("loans", LOAN_SCENARIOS),
                          ("increasing_annuities", INCREASING_SCENARIOS), ("retirement", RETIREMENT_SCENARIOS),
                          ("broker", BROKER_SCENARIOS)):
        for sid, params in table.items():
            out.append(dict(id=f"{module}/{sid}", module=module, params=dict(params), file_group=f"{module}/{sid}"))
    return out
