"""Registry of the places where Python intentionally differs from Excel.

For each defect this file holds three things:

1. **Where it applies** - ``defect_for(module, output, params)`` returns the
   defect ID for an output cell, or ``None`` if the Excel formula is correct.
2. **Excel's formula, bug for bug** - ``excel_replica(...)`` recomputes the
   workbook's (wrong) value. If it equals Excel's actual result, the
   diagnosis of *why* Excel differs is proven, not guessed.
3. **An independent check of Python** - ``verify_python(...)`` tests the
   Python answer by a different route (brute-force cash-flow sums,
   period-by-period loops, or plugging the answer back in).

A difference between Excel and Python is accepted only when all three agree.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from calculator.common import RateType, Timing
from calculator.single_investment import Outcome, growth_factor
from calculator import rates

EA, EP, NOM, SIM, CON = (RateType.EFFECTIVE_ANNUAL, RateType.EFFECTIVE_PERIODIC, RateType.NOMINAL,
                         RateType.SIMPLE, RateType.CONTINUOUS)


@dataclass(frozen=True)
class Discrepancy:
    id: str
    sheet: str
    title: str
    excel: str
    python: str


REGISTRY = {d.id: d for d in [
    Discrepancy("D1", "Rate converters (all 5 grids)", "Nominal → effective annual uses a fixed 12",
                "(1 + i(p)/p)^12 − 1", "(1 + i(p)/p)^p − 1"),
    Discrepancy("D2", "Rate converters", "→ continuous raises the logarithm to a power",
                "LN(1+i)^n (grids 1–5), and LN(1+i)^(n·p) for nominal (grids 1 and 5)",
                "δ = ln(1 + i)"),
    Discrepancy("D3", "Rate converters", "Continuous → effective annual returns a periodic rate",
                "e^(δ/(n·p)) − 1", "e^δ − 1"),
    Discrepancy("D4", "Rate converters", "Continuous → continuous is missing",
                "\"ERROR\"", "δ (unchanged)"),
    Discrepancy("D5", "Rate converters", "The term (Years) is used inconsistently",
                "simple/continuous cells ignore Years in one direction and use it in the other",
                "equivalence over n years: 1 + r·p·n = (1 + i)^n; identical to Excel when Years = 1"),
    Discrepancy("D6", "Loans converter (grid 4)", "Simple → periodic/nominal/simple reads blank cells",
                "0", "correct conversion"),
    Discrepancy("D7", "Increasing-annuities converter (grid 5)", "Simple → periodic/nominal/simple is broken",
                "#REF!", "correct conversion"),
    Discrepancy("D8", "2. SINGLE INVESTMENTS", "Interest earned mixes two questions",
                "FV(from PV) − PV(from FV)", "FV(from PV) − PV"),
    Discrepancy("D9", "2. SINGLE INVESTMENTS", "Effective annual rate: operator precedence",
                "(FV/PV)^(1/n·p) − 1, i.e. exponent p/n", "(FV/PV)^(1/n) − 1"),
    Discrepancy("D10", "2. SINGLE INVESTMENTS", "Interest earned (continuous) reads a blank cell",
                "0", "PV·(e^(δn) − 1)"),
    Discrepancy("D11", "3. ANNUITIES", "FV in arrears: misplaced bracket",
                "(X(1+i)^n − 1)/i", "X((1+i)^n − 1)/i"),
    Discrepancy("D12", "3. ANNUITIES", "Years in advance multiply by (1+i) instead of dividing",
                "ln(1 + FV·i·(1+i)/X)/ln(1+i)", "ln(1 + FV·i/(X(1+i)))/ln(1+i)"),
    Discrepancy("D13", "3. ANNUITIES", "\"Interest\" outputs are value ratios, not rates",
                "e.g. (X(1+i)^n − 1)/FV", "the rate i solving X·s_n(i) = FV (bisection)"),
    Discrepancy("D14", "4.LOANS", "Advance: payments needed uses the arrears formula",
                "−ln(1 − L·i/X)/ln(1+i)", "−ln(1 − L·d/X)/ln(1+i),  d = i/(1+i)"),
    Discrepancy("D15", "4.LOANS", "Advance: interest component uses i instead of d",
                "B_t · i", "B_t · d  (0 for the first payment)"),
    Discrepancy("D16", "4.LOANS", "\"Balance after T+1\" has no financial meaning",
                "years × last payment − X", "balance at year T + 1: L(1+i)^t' − X·s_t',  t' = (T+1)·p"),
    Discrepancy("D17", "3. ANNUITIES / 4.LOANS / 2. SINGLE INVESTMENTS",
                "Dropdowns copy a value, so the chosen rate/term goes stale",
                "e.g. Q8 = 2.0201% matches neither option any more", "the selected rate is always live"),
    Discrepancy("D18", "TEB", "Broken INDIRECT names, stale price copies, volatile RAND(), Excel-365-only FX",
                "3 companies unusable, results change on every edit",
                "direct price lookup, seeded simulation, editable/live FX"),
]}


# ---------------------------------------------------------------------------
# 1. Where each defect applies
# ---------------------------------------------------------------------------

_CONVERTER_DEFECTS = {
    (NOM, EA): "D1",
    (EA, CON): "D2",
    (CON, EA): "D3",
    (CON, CON): "D4",
    **{pair: "D5" for pair in [(EA, SIM), (EP, SIM), (NOM, SIM), (SIM, EA), (SIM, CON),
                               (CON, EP), (CON, NOM), (CON, SIM)]},
}


def defect_for(module: str, output: str, params: dict) -> str | None:
    if module.startswith("rate_converter_grid"):
        grid = int(module[-1])
        pair = (RateType(params["from_type"]), RateType(params["to_type"]))
        if pair == (NOM, CON):
            return "D2" if grid in (1, 5) else "D5"
        if pair[0] is SIM and pair[1] in (EP, NOM, SIM):
            return {4: "D6", 5: "D7"}.get(grid, "D5")
        return _CONVERTER_DEFECTS.get(pair)
    if module == "single_investment":
        outcome, rtype = Outcome(params["outcome"]), RateType(params["interest_type"])
        if outcome is Outcome.INTEREST_EARNED and output == "answer":
            return "D10" if rtype is CON else "D8"
        if outcome is Outcome.INTEREST_RATE and rtype is EA and output == "rate_out":
            return "D9"
        return None
    if module == "annuities":
        return {"arrears.future_value": "D11", "advance.years_from_fv": "D12",
                "advance.years_from_pv": "D12"}.get(output) or ("D13" if ".rate_from_" in output else None)
    if module == "loans":
        return {"advance.payments_needed": "D14", "advance.last_payment": "D14",
                "advance.interest_next_payment": "D15", "advance.capital_next_payment": "D15",
                "arrears.balance_at_T_plus_1": "D16"}.get(output)
    return None


# ---------------------------------------------------------------------------
# 2. Excel's formulas, bug for bug
# ---------------------------------------------------------------------------

NUM_ERROR = "#NUM!"


def _excel_ln(x: float):
    return math.log(x) if x > 0 else NUM_ERROR


def excel_converter(grid: int, i: float, f: RateType, t: RateType, pf: float, pt: float, nf: float, nt: float):
    """The BACKROOM1 conversion grid exactly as written in the workbook."""
    e = math.e
    if f is EA:
        return {EA: i, EP: (1 + i) ** (1 / pt) - 1, NOM: ((1 + i) ** (1 / pt) - 1) * pt,
                SIM: i / (nt * pt), CON: math.log(1 + i) ** nf}[t]
    if f is EP:
        return {EA: (1 + i) ** pf - 1, EP: (1 + i) ** (pf / pt) - 1, NOM: ((1 + i) ** (pf / pt) - 1) * pt,
                SIM: ((1 + i) ** pf - 1) / pt, CON: math.log((1 + i) ** pf)}[t]
    if f is NOM:
        con = math.log(1 + i) ** (nf * pf) if grid in (1, 5) else math.log(1 + i / pf) * (pf * nf)
        return {EA: (1 + i / pf) ** 12 - 1, EP: (1 + i / pf) ** (pf / pt) - 1,
                NOM: ((1 + i / pf) ** (pf / pt) - 1) * pt, SIM: ((1 + i / pf) ** pf - 1) / pt, CON: con}[t]
    if f is SIM:
        if t is EA:
            return (1 + i * pf) - 1
        if t is CON:
            return math.log(1 + nf * i * pf)
        if grid == 4:
            return 0.0   # references blank cells AJ23/AJ24
        if grid == 5:
            return "#REF!"
        return {EP: (1 + i * pf) ** (1 / pt) - 1, NOM: ((1 + i * pf) ** (1 / pt) - 1) * pt,
                SIM: ((1 + i * pf) - 1) / pt}[t]
    # f is CON
    if t is CON:
        return "ERROR"
    return {EA: e ** (i / (nt * pt)) - 1, EP: e ** (i / (pt * nt)) - 1,
            NOM: (e ** (i / (pt * nt)) - 1) * pt, SIM: (e ** i - 1) / (nt * pt)}[t]


def excel_replica(module: str, output: str, params: dict):
    """Excel's value for a defective output cell, recomputed from its formula."""
    p = params
    if module.startswith("rate_converter_grid"):
        return excel_converter(int(module[-1]), p["value"], RateType(p["from_type"]), RateType(p["to_type"]),
                               p["from_periods"], p["to_periods"], p["from_years"], p["to_years"])

    if module == "single_investment":
        rtype, outcome = RateType(p["interest_type"]), Outcome(p["outcome"])
        n, per = p["years"], p["periods_per_year"]
        if outcome is Outcome.INTEREST_EARNED:
            if rtype is CON:
                return 0.0  # blank BACKROOM1!P28
            g = growth_factor(p["rate"], rtype, n, per)
            return p["pv"] * g - p["fv"] / g  # L - M
        if outcome is Outcome.INTEREST_RATE and rtype is EA:
            return (p["fv"] / p["pv"]) ** (1 / n * per) - 1
        return None

    if module == "annuities":
        x, i, fv, pv = p["installment"], p["rate"], p["fv"], p["pv"]
        n = p["years"] * p["periods_per_year"]
        v_n = (1 + i) ** (-n)
        if output == "arrears.future_value":
            return (x * (1 + i) ** n - 1) / i
        if output == "advance.years_from_fv":
            arg = (fv * i) / x * (1 + i) + 1  # BACKROOM1!U12
            ln = _excel_ln(arg)
            return ln if isinstance(ln, str) else ln / math.log(1 + i) / p["periods_per_year"]
        if output == "advance.years_from_pv":
            arg = -((pv * i) / x * (1 + i) - 1)  # BACKROOM1!U13
            ln = _excel_ln(arg)
            return ln if isinstance(ln, str) else ln / math.log(1 / (1 + i)) / p["periods_per_year"]
        return {"arrears.rate_from_fv": (x * (1 + i) ** n - 1) / fv,
                "advance.rate_from_fv": x * (1 + i) * ((1 + i) ** n - 1) / fv,
                "arrears.rate_from_pv": x * (1 - v_n) / pv,
                "advance.rate_from_pv": x * (1 + i) * (1 - v_n) / pv}[output]

    if module == "loans":
        L, x, i = p["principal"], p["installment"], p["rate"]
        per, years = p["periods_per_year"], p["years"]
        t = p["year_T"] * per

        def roundup_arrears_n():  # '4.LOANS'!P32 / U32
            ln = _excel_ln(1 - L * i / x)
            return ln if isinstance(ln, str) else math.ceil(-ln / math.log(1 + i))

        if output == "advance.payments_needed":
            return roundup_arrears_n()
        if output == "advance.last_payment":
            N = roundup_arrears_n()
            if isinstance(N, str):
                return N
            return L * (1 + i) ** (N - 1) - x * (1 + i) * ((1 + i) ** (N - 1) - 1) / i
        b_adv = L * (1 + i) ** t - x * (1 + i) * ((1 + i) ** t - 1) / i  # U29
        if output == "advance.interest_next_payment":
            return b_adv * i
        if output == "advance.capital_next_payment":
            return x - b_adv * i
        if output == "arrears.balance_at_T_plus_1":
            N = roundup_arrears_n()
            if isinstance(N, str):
                return N
            last = (L * (1 + i) ** (N - 1) - x * ((1 + i) ** (N - 1) - 1) / i) * (1 + i)  # P33
            return years * last - x
    return None


# ---------------------------------------------------------------------------
# 3. Independent checks of the Python answer
# ---------------------------------------------------------------------------

def _close(a: float, b: float, rel: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


def _is_whole(x: float) -> bool:
    return abs(x - round(x)) < 1e-9


def verify_python(module: str, output: str, params: dict, value) -> tuple[bool | None, str]:
    """Check a Python result by a different route. Returns (passed, how)."""
    p = params

    if module.startswith("rate_converter_grid"):
        # Same accumulated value over the term, using growth factors (not rates.py).
        f, t = RateType(p["from_type"]), RateType(p["to_type"])
        ea_from = growth_factor(p["value"], f, p["from_years"], p["from_periods"]) ** (1 / p["from_years"]) - 1
        ea_to = growth_factor(value, t, p["to_years"], p["to_periods"]) ** (1 / p["to_years"]) - 1
        return _close(ea_from, ea_to), "both rates give the same effective annual growth (growth-factor check)"

    if module == "single_investment":
        rtype, outcome = RateType(p["interest_type"]), Outcome(p["outcome"])
        if outcome is Outcome.INTEREST_EARNED:
            i = rates.to_effective_annual(p["rate"], rtype, p["periods_per_year"], p["years"])
            expected = p["pv"] * ((1 + i) ** p["years"] - 1)
            return _close(value, expected), "PV·((1 + i)^n − 1) with i from the rate converter"
        if outcome is Outcome.INTEREST_RATE:
            return _close(p["pv"] * (1 + value) ** p["years"], p["fv"]), "PV·(1 + rate)^n reproduces FV"

    if module == "annuities":
        x, i, fv, pv, per = p["installment"], p["rate"], p["fv"], p["pv"], p["periods_per_year"]
        n = p["years"] * per
        advance = output.startswith("advance")
        if output == "arrears.future_value":
            if not _is_whole(n):
                return None, "not applicable (fractional number of payments)"
            brute = sum(x * (1 + i) ** (round(n) - k) for k in range(1, round(n) + 1))
            return _close(value, brute), "sum of every payment accumulated to the end"
        if output == "advance.years_from_fv":
            m = value * per
            return _close(x * (1 + i) * ((1 + i) ** m - 1) / i, fv), "X·s̈_n with this n reproduces FV"
        if output == "advance.years_from_pv":
            m = value * per
            return _close(x * (1 + i) * (1 - (1 + i) ** -m) / i, pv), "X·ä_n with this n reproduces PV"
        if ".rate_from_fv" in output:
            j = value
            fv_check = x * ((1 + j) ** n - 1) / j * ((1 + j) if advance else 1)
            return _close(fv_check, fv, 1e-7), "X·s_n at this rate reproduces FV"
        if ".rate_from_pv" in output:
            j = value
            pv_check = x * (1 - (1 + j) ** -n) / j * ((1 + j) if advance else 1)
            return _close(pv_check, pv, 1e-7), "X·a_n at this rate reproduces PV"

    if module == "loans":
        L, x, i, per = p["principal"], p["installment"], p["rate"], p["periods_per_year"]
        t = p["year_T"] * per
        if output in ("advance.payments_needed", "advance.last_payment"):
            balance, count, last = L, 0, None
            while count < 10_000:
                payment = min(x, balance)  # payment at the start of the period
                balance -= payment
                count += 1
                last = payment
                if balance <= 1e-9:
                    break
                balance *= 1 + i
            target = count if output == "advance.payments_needed" else last
            return _close(value, target), "period-by-period repayment loop"
        if output in ("advance.interest_next_payment", "advance.capital_next_payment"):
            if not _is_whole(t):
                return None, "not applicable (fractional payment number)"
            balance, interest = L, 0.0
            for k in range(round(t) + 1):  # payments 1 .. t+1, made at times 0 .. t
                interest = 0.0 if k == 0 else balance * i
                balance = balance + interest - x
            target = interest if output.endswith("interest_next_payment") else x - interest
            return _close(value, target), "period-by-period loop: interest accrued since the previous payment"
        if output == "arrears.balance_at_T_plus_1":
            t1 = (p["year_T"] + 1) * per
            if not _is_whole(t1):
                return None, "not applicable (fractional payment number)"
            balance = L
            for _ in range(round(t1)):
                balance = balance * (1 + i) - x
            return _close(value, balance), "period-by-period balance loop"

    return None, "no independent check defined"
