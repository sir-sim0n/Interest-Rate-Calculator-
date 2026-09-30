"""Single (lump-sum) investments ('2. SINGLE INVESTMENTS' + BACKROOM1!K23:P28).

Everything on this sheet rests on one idea: the **growth factor**, i.e. what
1 rand grows to after ``years`` under a given kind of interest.

==================  ======================  ==========================
Interest type       Growth factor           Excel (row in BACKROOM1)
==================  ======================  ==========================
Simple              1 + r * n * p           L24  (r = simple rate per period)
Effective periodic  (1 + j)^(n * p)         L25  (j = rate per period)
Effective annual    (1 + i)^n               L26
Nominal             (1 + i(p)/p)^(n * p)    L27
Continuous          e^(delta * n)           L28
==================  ======================  ==========================

With the growth factor ``g``:

* future value      FV = PV * g                       (column L)
* present value     PV = FV / g                       (column M)
* interest earned   FV - PV  (on the given PV)        (column P)
* term / rate       invert g for years or for the rate (columns N and O)

Differences from Excel (see docs/validation_report.md):
* D8  Excel's "interest earned" is FV(from PV) - PV(from FV); here it is FV - PV.
* D9  Excel's effective-annual rate uses (FV/PV)^(p/n); here (FV/PV)^(1/n).
* D10 Excel returns 0 for continuous "interest earned"; here it is calculated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .common import (
    CalculationError,
    RateType,
    require_non_negative,
    require_positive,
    require_rate,
)


class Outcome(str, Enum):
    """What the user wants to solve for ('2. SINGLE INVESTMENTS'!K13)."""

    FUTURE_VALUE = "Future value"
    PRESENT_VALUE = "Present value"
    YEARS = "Years"
    INTEREST_RATE = "Interest rate"
    INTEREST_EARNED = "Interest earned"


def growth_factor(rate: float, interest_type: RateType, years: float, periods_per_year: float = 1) -> float:
    """Accumulated value of 1 after ``years`` (BACKROOM1!L24:L28 with PV = 1)."""
    interest_type = RateType(interest_type)
    n = require_non_negative("Years", years)
    p = require_positive("Periods per year", periods_per_year)

    if interest_type is RateType.SIMPLE:
        g = 1 + rate * n * p
    elif interest_type is RateType.EFFECTIVE_PERIODIC:
        require_rate("Interest rate", rate)
        g = (1 + rate) ** (n * p)
    elif interest_type is RateType.EFFECTIVE_ANNUAL:
        require_rate("Interest rate", rate)
        g = (1 + rate) ** n
    elif interest_type is RateType.NOMINAL:
        if 1 + rate / p <= 0:
            raise CalculationError("The nominal rate must be greater than -p × 100%.")
        g = (1 + rate / p) ** (n * p)
    else:  # CONTINUOUS
        g = math.exp(rate * n)

    if g <= 0:
        raise CalculationError("These inputs give a zero or negative accumulated value.")
    return g


def future_value(pv: float, rate: float, interest_type: RateType, years: float, periods_per_year: float = 1) -> float:
    """FV = PV x growth factor  (BACKROOM1!L24:L28)."""
    return pv * growth_factor(rate, interest_type, years, periods_per_year)


def present_value(fv: float, rate: float, interest_type: RateType, years: float, periods_per_year: float = 1) -> float:
    """PV = FV / growth factor  (BACKROOM1!M24:M28)."""
    return fv / growth_factor(rate, interest_type, years, periods_per_year)


def interest_earned(pv: float, rate: float, interest_type: RateType, years: float, periods_per_year: float = 1) -> float:
    """Interest earned on ``pv`` over the term: FV - PV  (replaces BACKROOM1!P24:P28, D8/D10)."""
    return future_value(pv, rate, interest_type, years, periods_per_year) - pv


def _value_ratio(pv: float, fv: float) -> float:
    require_positive("Present value", pv)
    require_positive("Future value", fv)
    return fv / pv


def solve_years(pv: float, fv: float, rate: float, interest_type: RateType, periods_per_year: float = 1) -> float:
    """Years needed for ``pv`` to grow to ``fv``  (BACKROOM1!N24:N28)."""
    interest_type = RateType(interest_type)
    ratio = _value_ratio(pv, fv)
    p = require_positive("Periods per year", periods_per_year)

    if interest_type is RateType.SIMPLE:
        per_year = rate * p
        if per_year == 0:
            raise CalculationError("The interest rate cannot be zero when solving for years.")
        years = (ratio - 1) / per_year
    elif interest_type is RateType.CONTINUOUS:
        if rate == 0:
            raise CalculationError("The interest rate cannot be zero when solving for years.")
        years = math.log(ratio) / rate
    else:
        # Compound types: ratio = (1 + j)^(periods), solve for the number of periods.
        if interest_type is RateType.EFFECTIVE_PERIODIC:
            per_period, periods_in_a_year = rate, p
        elif interest_type is RateType.EFFECTIVE_ANNUAL:
            per_period, periods_in_a_year = rate, 1
        else:  # NOMINAL
            per_period, periods_in_a_year = rate / p, p
        require_rate("Interest rate per period", per_period)
        if per_period == 0:
            raise CalculationError("The interest rate cannot be zero when solving for years.")
        years = math.log(ratio) / math.log(1 + per_period) / periods_in_a_year

    if years < 0:
        raise CalculationError("With this rate the investment never reaches the future value.")
    return years


def solve_rate(pv: float, fv: float, years: float, interest_type: RateType, periods_per_year: float = 1) -> float:
    """Rate (of ``interest_type``) that grows ``pv`` to ``fv`` in ``years``  (BACKROOM1!O24:O28)."""
    interest_type = RateType(interest_type)
    ratio = _value_ratio(pv, fv)
    n = require_positive("Years", years)
    p = require_positive("Periods per year", periods_per_year)

    if interest_type is RateType.SIMPLE:
        return (ratio - 1) / (n * p)
    if interest_type is RateType.EFFECTIVE_PERIODIC:
        return ratio ** (1 / (n * p)) - 1
    if interest_type is RateType.EFFECTIVE_ANNUAL:
        return ratio ** (1 / n) - 1  # D9: Excel uses ratio^(p/n)
    if interest_type is RateType.NOMINAL:
        return p * (ratio ** (1 / (n * p)) - 1)
    return math.log(ratio) / n  # CONTINUOUS


def solve(
    outcome: Outcome,
    interest_type: RateType,
    *,
    pv: float,
    fv: float,
    rate: float,
    years: float,
    periods_per_year: float = 1,
) -> float:
    """Answer the question chosen in K13/K14 (replaces the nested IFs in K16:K18)."""
    outcome = Outcome(outcome)
    if outcome is Outcome.FUTURE_VALUE:
        return future_value(pv, rate, interest_type, years, periods_per_year)
    if outcome is Outcome.PRESENT_VALUE:
        return present_value(fv, rate, interest_type, years, periods_per_year)
    if outcome is Outcome.INTEREST_EARNED:
        return interest_earned(pv, rate, interest_type, years, periods_per_year)
    if outcome is Outcome.YEARS:
        return solve_years(pv, fv, rate, interest_type, periods_per_year)
    return solve_rate(pv, fv, years, interest_type, periods_per_year)


def compare_interest_types(pv: float, rate: float, years: float, periods_per_year: float = 1) -> dict[RateType, float]:
    """FV of ``pv`` under every interest type (the data behind Excel's Chart 1)."""
    return {t: future_value(pv, rate, t, years, periods_per_year) for t in RateType}


@dataclass(frozen=True)
class GrowthRow:
    year: float
    value: float
    interest_to_date: float


def growth_table(
    pv: float, rate: float, interest_type: RateType, years: float, periods_per_year: float = 1
) -> list[GrowthRow]:
    """Year-by-year value of the investment.

    Replaces the leftover growth tables at '2. SINGLE INVESTMENTS'!AO13:AS24,
    one of which depended on an external workbook. Rows are for year 0, 1, 2,
    ... and a final row at exactly ``years`` if the term is fractional.
    """
    n = require_non_negative("Years", years)
    points = [float(k) for k in range(int(math.floor(n)) + 1)]
    if n > points[-1]:
        points.append(n)
    rows = []
    for t in points:
        value = future_value(pv, rate, interest_type, t, periods_per_year)
        rows.append(GrowthRow(year=t, value=value, interest_to_date=value - pv))
    return rows
