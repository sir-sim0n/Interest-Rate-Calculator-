"""Run every Excel scenario through Python and compare the results.

Used by ``tests/test_excel_parity.py`` (pass/fail) and by
``tools/generate_validation_report.py`` (the Markdown report).

Comparison rules
----------------
* Numbers match when they agree to a relative tolerance of 1e-9 (about nine
  significant figures). Any real formula difference is far larger; genuine
  floating-point differences are around 1e-15.
* An Excel error (``#NUM!``, ``#DIV/0!``, ``#REF!``, ``"ERROR"``) matches a
  Python ``CalculationError``: both say "cannot be calculated".
* Excel's ``"-"`` (not applicable) matches Python's ``"-"``.
* Any other difference must be a registered defect, Excel's value must be
  reproduced by that defect's formula, and the Python value must pass an
  independent check. Otherwise the comparison fails.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from calculator import broker, increasing_annuities as ia, loans, rates, single_investment as si
from calculator import annuities
from calculator.common import CalculationError, RateType, Timing
from calculator.single_investment import Outcome
from validation.known_discrepancies import defect_for, excel_replica, verify_python

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REL_TOL = 1e-9
ABS_TOL = 1e-9


class PythonError(str):
    """A Python CalculationError, kept as its message."""


def _safe(func):
    try:
        return func()
    except CalculationError as exc:
        return PythonError(str(exc))


# ---------------------------------------------------------------------------
# Python side: one function per module, returning {output name: value}
# ---------------------------------------------------------------------------

def _converter(p):
    return {"converted_rate": _safe(lambda: rates.convert_rate(
        p["value"], RateType(p["from_type"]), RateType(p["to_type"]),
        p["from_periods"], p["to_periods"], p["from_years"], p["to_years"]))}


def _single_investment(p):
    outcome = Outcome(p["outcome"])
    value = _safe(lambda: si.solve(outcome, RateType(p["interest_type"]), pv=p["pv"], fv=p["fv"],
                                   rate=p["rate"], years=p["years"], periods_per_year=p["periods_per_year"]))
    out = {"answer": "-", "years_out": "-", "rate_out": "-"}  # K16:K18 show "-" when not applicable
    key = {Outcome.YEARS: "years_out", Outcome.INTEREST_RATE: "rate_out"}.get(outcome, "answer")
    out[key] = value
    return out


def _annuities(p):
    out = {}
    for timing in Timing:
        res = annuities.annuity_summary(installment=p["installment"], rate=p["rate"], years=p["years"],
                                        periods_per_year=p["periods_per_year"], pv=p["pv"], fv=p["fv"],
                                        timing=timing)
        for name in ("future_value", "present_value", "years_from_fv", "years_from_pv",
                     "installment_from_fv", "installment_from_pv", "rate_from_fv", "rate_from_pv"):
            value = getattr(res, name)
            out[f"{timing.value.lower()}.{name}"] = PythonError(res.errors[name]) if value is None else value
    return out


def _loans(p):
    out = {}
    for timing in Timing:
        res = loans.loan_summary(principal=p["principal"], installment_=p["installment"], rate=p["rate"],
                                 years=p["years"], periods_per_year=p["periods_per_year"],
                                 year_T=p["year_T"], timing=timing)
        for name in ("installment", "loan_amount", "balance_at_T", "interest_next_payment",
                     "capital_next_payment", "payments_needed", "last_payment", "capital_in_year_T",
                     "interest_in_year_T", "total_interest", "balance_at_T_plus_1"):
            value = getattr(res, name)
            error = res.errors.get(name) or res.errors.get("interest_next_payment", "")
            out[f"{timing.value.lower()}.{name}"] = PythonError(error) if value is None else value
    return out


def _increasing(p):
    out = {}
    for timing in Timing:
        stepped = ia.stepped_summary(payment=p["payment"], rate=p["rate"], growth=p["growth"], k=p["k"],
                                     m=p["m"], pv=p["pv"], fv=p["fv"], timing=timing)
        geometric = ia.geometric_summary(payment=p["payment"], rate=p["rate"], growth=p["growth"],
                                         years=p["years"], periods_per_year=p["periods_per_year"],
                                         pv=p["pv"], fv=p["fv"], timing=timing)
        for kind, res in (("stepped", stepped), ("geometric", geometric)):
            for name in ("installment_from_fv", "installment_from_pv", "future_value", "present_value"):
                out[f"{kind}.{timing.value.lower()}.{name}"] = getattr(res, name)
    return out


def _retirement(p):
    res = ia.plan_retirement(ia.RetirementInputs(**p))
    return {name: getattr(res, name) for name in
            ("first_withdrawal", "withdrawals_fv", "withdrawals_pv", "lump_sum_fv", "first_contribution")}


def _broker(p):
    data = broker.market_data()
    by_exchange = data.company(p["exchange_company"])      # price from Python's own data file
    by_country = data.company(p["country_company"])
    exchange_usd = broker.purchase_cost_usd(by_exchange.price_usd, p["exchange_shares"])
    country_usd = broker.purchase_cost_usd(by_country.price_usd, p["country_shares"])
    country_zar = broker.to_zar(country_usd, p["usd_zar"])
    annual_return = p[f"return.{p['country']}"]
    return {
        "exchange_cost_usd": exchange_usd,
        "exchange_cost_zar": broker.to_zar(exchange_usd, p["usd_zar"]),
        "country_cost_usd": country_usd,
        "country_cost_zar": country_zar,
        "projected_value": broker.projected_value(country_zar, annual_return, p["years"]),
    }


def python_outputs(module: str, params: dict) -> dict:
    if module.startswith("rate_converter_grid"):
        return _converter(params)
    return {"single_investment": _single_investment, "annuities": _annuities, "loans": _loans,
            "increasing_annuities": _increasing, "retirement": _retirement, "broker": _broker}[module](params)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

@dataclass
class Comparison:
    source: str          # "excel" (saved values) or "libreoffice" (recalculated scenarios)
    scenario: str
    module: str
    output: str
    cell: str
    excel: object
    python: object
    status: str          # "match" | "known" | "FAIL"
    defect: str | None = None
    note: str = ""


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_excel_error(x) -> bool:
    return isinstance(x, str) and (x.startswith("#") or x == "ERROR")


def values_agree(excel, python) -> bool:
    if _is_number(excel) and _is_number(python):
        return math.isclose(excel, python, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    if _is_excel_error(excel) and isinstance(python, PythonError):
        return True
    return excel == python and not isinstance(python, PythonError)


def compare_scenario(source: str, scenario: dict) -> list[Comparison]:
    module, params = scenario["module"], scenario["params"]
    py = python_outputs(module, params)
    rows = []
    for output, excel in scenario["outputs"].items():
        python = py[output]
        row = Comparison(source, scenario["id"], module, output, scenario["cells"][output], excel, python, "match")
        defect = defect_for(module, output, params)
        if values_agree(excel, python):
            if defect:
                row.note = f"{defect} is in this formula but has no effect for these inputs"
        elif defect is None:
            row.status, row.note = "FAIL", "unexplained difference"
        else:
            row.defect = defect
            replica = excel_replica(module, output, params)
            # A broken reference shows as #REF! in Excel but #NAME? in LibreOffice
            # (the formula text literally contains "#REF!"), so any two error
            # values count as the same outcome.
            explained = values_agree(replica, excel) or replica == excel or (
                _is_excel_error(replica) and _is_excel_error(excel))
            if isinstance(python, PythonError):
                verified, how = True, f"Python reports: {python}"
            else:
                verified, how = verify_python(module, output, params, python)
            if not explained:
                row.status, row.note = "FAIL", f"{defect} formula does not reproduce Excel ({replica!r})"
            elif verified is False:
                row.status, row.note = "FAIL", f"Python failed its independent check: {how}"
            else:
                row.status = "known"
                row.note = f"Excel reproduced by the {defect} formula; Python checked: {how}"
        rows.append(row)
    return rows


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def all_comparisons() -> list[Comparison]:
    rows = []
    for source, filename in (("excel", "excel_saved_values.json"), ("libreoffice", "excel_scenarios.json")):
        path = FIXTURES / filename
        if not path.exists():
            continue
        for scenario in load_fixture(filename)["scenarios"]:
            rows.extend(compare_scenario(source, scenario))
    return rows
