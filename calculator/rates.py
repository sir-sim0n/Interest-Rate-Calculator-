"""Interest-rate conversions ('1. RATE CONVERTER' and the embedded converters).

How Excel does it
-----------------
BACKROOM1 holds a 5 x 5 grid (rows = "from" type, columns = "to" type) with a
separate formula in each of the 24 filled cells, and the output cell O17 picks
one cell with a 24-branch nested IF. The grid is copied five times (once for
each sheet that has a converter), and the copies are not identical.

How Python does it (hub-and-spoke)
----------------------------------
Every rate type is converted *to* the effective annual rate ``i`` and then
*from* ``i`` to the target type. Two small functions with five formulas each
replace all 120 grid formulas:

====================  ==============================  ==============================
Rate type             to effective annual  i = ...     from effective annual  ... =
====================  ==============================  ==============================
Effective annual  i   i                               i
Effective periodic j  (1 + j)^p - 1                   (1 + i)^(1/p) - 1
Nominal       i(p)    (1 + i(p)/p)^p - 1              p * ((1 + i)^(1/p) - 1)
Simple (per period) r (1 + r*p*n)^(1/n) - 1           ((1 + i)^n - 1) / (n*p)
Continuous    delta   e^delta - 1                     ln(1 + i)
====================  ==============================  ==============================

Conventions kept from the workbook:
* A *simple* rate is quoted per period, so ``r*p`` is the simple rate per
  year (Excel: simple -> effective annual = ``r * p``).
* Simple interest does not compound, so its equivalence with a compound rate
  depends on the term ``n``. Two rates are equivalent when they give the same
  accumulated value over ``n`` years: ``1 + r*p*n = (1 + i)^n``.
  With ``n = 1`` (the workbook's usual input) this reduces exactly to Excel.

The "Years" inputs only affect *simple* rates, because for compound and
continuous rates the equivalence is the same for every term.
"""

from __future__ import annotations

import math

from .common import CalculationError, RateType, require_positive, require_rate


def to_effective_annual(
    rate: float,
    rate_type: RateType,
    periods_per_year: float = 1,
    years: float = 1,
) -> float:
    """Convert a quoted rate to the equivalent effective annual rate ``i``."""
    rate_type = RateType(rate_type)
    p = require_positive("Periods per year", periods_per_year)

    if rate_type is RateType.EFFECTIVE_ANNUAL:
        return require_rate("Effective annual rate", rate)

    if rate_type is RateType.EFFECTIVE_PERIODIC:
        require_rate("Effective periodic rate", rate)
        return (1 + rate) ** p - 1

    if rate_type is RateType.NOMINAL:
        if 1 + rate / p <= 0:
            raise CalculationError("The nominal rate must be greater than -p × 100%.")
        return (1 + rate / p) ** p - 1

    if rate_type is RateType.SIMPLE:
        n = require_positive("Years", years)
        growth = 1 + rate * p * n  # accumulated value of 1 under simple interest
        if growth <= 0:
            raise CalculationError("This simple rate would make the accumulated value negative.")
        return growth ** (1 / n) - 1

    if rate_type is RateType.CONTINUOUS:
        return math.exp(rate) - 1

    raise CalculationError(f"Unknown rate type: {rate_type}")  # pragma: no cover


def from_effective_annual(
    i: float,
    rate_type: RateType,
    periods_per_year: float = 1,
    years: float = 1,
) -> float:
    """Express an effective annual rate ``i`` as a rate of ``rate_type``."""
    rate_type = RateType(rate_type)
    p = require_positive("Periods per year", periods_per_year)
    require_rate("Effective annual rate", i)

    if rate_type is RateType.EFFECTIVE_ANNUAL:
        return i
    if rate_type is RateType.EFFECTIVE_PERIODIC:
        return (1 + i) ** (1 / p) - 1
    if rate_type is RateType.NOMINAL:
        return p * ((1 + i) ** (1 / p) - 1)
    if rate_type is RateType.SIMPLE:
        n = require_positive("Years", years)
        return ((1 + i) ** n - 1) / (n * p)
    if rate_type is RateType.CONTINUOUS:
        return math.log(1 + i)

    raise CalculationError(f"Unknown rate type: {rate_type}")  # pragma: no cover


def convert_rate(
    rate: float,
    from_type: RateType,
    to_type: RateType,
    from_periods: float = 1,
    to_periods: float = 1,
    from_years: float = 1,
    to_years: float = 1,
) -> float:
    """Convert ``rate`` from one quotation to another.

    Mirrors the inputs of '1. RATE CONVERTER':
    P11 rate, P13 from_type, P12 from_periods, P14 from_years,
    R13 to_type, R12 to_periods, R14 to_years  ->  O17 converted rate.
    """
    from_type, to_type = RateType(from_type), RateType(to_type)

    # Converting a rate to exactly the same quotation returns it unchanged
    # (avoids a round trip through ``i`` that would add floating-point noise).
    if from_type is to_type and from_periods == to_periods and (
        from_type is not RateType.SIMPLE or from_years == to_years
    ):
        require_positive("Periods per year", from_periods)
        return float(rate)

    i = to_effective_annual(rate, from_type, from_periods, from_years)
    return from_effective_annual(i, to_type, to_periods, to_years)


def equivalent_rates(
    rate: float,
    from_type: RateType,
    from_periods: float = 1,
    from_years: float = 1,
    to_periods: float = 1,
    to_years: float = 1,
) -> dict[RateType, float]:
    """The rate expressed in all five quotations (used for the summary table)."""
    return {
        target: convert_rate(rate, from_type, target, from_periods, to_periods, from_years, to_years)
        for target in RateType
    }
