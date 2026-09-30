"""Level annuities ('3. ANNUITIES').

A level annuity is ``n`` equal payments ``X``, one per period, at a rate ``i``
per period. Two standard factors do all the work (BWIA 111 notation):

    accumulation factor   s_n = ((1 + i)^n - 1) / i          -> FV = X * s_n
    present-value factor  a_n = (1 - (1 + i)^-n) / i         -> PV = X * a_n

Payments in advance (annuity-due) happen one period earlier, so every value
is multiplied by ``(1 + i)``:  s̈_n = (1 + i) s_n  and  ä_n = (1 + i) a_n.

Excel (sheet 3, column P = arrears, column R = advance):

======================  ==================================  =================
Output                  Python                              Excel
======================  ==================================  =================
FUTURE VALUE            future_value                        P24 / R24
PRESENT VALUE           present_value                       P25 / R25
NUMBER OF YEARS (FV)    term_from_fv / p                    P26 / R26
NUMBER OF YEARS (PV)    term_from_pv / p                    P27 / R27
INSTALLMENT (FV)        installment_from_fv                 P28 / R28
INSTALLMENT (PV)        installment_from_pv                 P29 / R29
INTEREST (FV)           rate_from_fv  (numerical solver)    P30 / R30
INTEREST (PV)           rate_from_pv  (numerical solver)    P31 / R31
======================  ==================================  =================

Differences from Excel (see docs/validation_report.md):
* D11 Excel's P24 has a misplaced bracket: (X(1+i)^n - 1)/i instead of X((1+i)^n - 1)/i.
* D12 Excel's R26/R27 multiply by (1 + i) where they should divide.
* D13 Excel's P30:R31 are ratios of values, not interest rates. There is no
  closed-form formula for the rate of an annuity, so it is found numerically.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .common import (
    CalculationError,
    Timing,
    is_zero,
    require_non_negative,
    require_positive,
    require_rate,
)


# --------------------------------------------------------------------------
# The two annuity factors
# --------------------------------------------------------------------------

def _timing_factor(i: float, timing: Timing) -> float:
    """1 for arrears, (1 + i) for advance."""
    return (1 + i) if Timing(timing) is Timing.ADVANCE else 1.0


def accumulation_factor(i: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """s_n (arrears) or s̈_n (advance): accumulated value of payments of 1."""
    require_rate("Interest rate", i)
    require_non_negative("Number of payments", n)
    s_n = n if is_zero(i) else ((1 + i) ** n - 1) / i  # i = 0: s_n = n
    return s_n * _timing_factor(i, timing)


def discount_factor(i: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """a_n (arrears) or ä_n (advance): present value of payments of 1."""
    require_rate("Interest rate", i)
    require_non_negative("Number of payments", n)
    a_n = n if is_zero(i) else (1 - (1 + i) ** -n) / i  # i = 0: a_n = n
    return a_n * _timing_factor(i, timing)


# --------------------------------------------------------------------------
# Values and installments
# --------------------------------------------------------------------------

def future_value(installment: float, i: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """FV = X * s_n  (Excel P24 / R24)."""
    return installment * accumulation_factor(i, n, timing)


def present_value(installment: float, i: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """PV = X * a_n  (Excel P25 / R25)."""
    return installment * discount_factor(i, n, timing)


def installment_from_fv(fv: float, i: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """Installment that accumulates to ``fv``: X = FV / s_n  (Excel P28 / R28)."""
    factor = accumulation_factor(i, require_positive("Number of payments", n), timing)
    return fv / factor


def installment_from_pv(pv: float, i: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """Installment with present value ``pv``: X = PV / a_n  (Excel P29 / R29)."""
    factor = discount_factor(i, require_positive("Number of payments", n), timing)
    return pv / factor


# --------------------------------------------------------------------------
# Number of payments (term)
# --------------------------------------------------------------------------

def term_from_fv(fv: float, installment: float, i: float, timing: Timing = Timing.ARREARS) -> float:
    """Number of payments needed to accumulate ``fv``.

    Solves X * t * ((1+i)^n - 1)/i = FV for n, where t = 1 (arrears) or 1+i (advance):
        n = ln(1 + FV*i / (X*t)) / ln(1 + i)          (Excel P26 / R26, D12)
    """
    require_positive("Installment", installment)
    require_non_negative("Future value", fv)
    require_rate("Interest rate", i)
    per_payment = installment * _timing_factor(i, timing)
    if is_zero(i):
        return fv / per_payment
    inside = 1 + fv * i / per_payment
    if inside <= 0:
        raise CalculationError("These payments can never accumulate to the future value at this rate.")
    return math.log(inside) / math.log(1 + i)


def term_from_pv(pv: float, installment: float, i: float, timing: Timing = Timing.ARREARS) -> float:
    """Number of payments with present value ``pv``.

    Solves X * t * (1 - (1+i)^-n)/i = PV for n:
        n = -ln(1 - PV*i / (X*t)) / ln(1 + i)         (Excel P27 / R27, D12)
    """
    require_positive("Installment", installment)
    require_non_negative("Present value", pv)
    require_rate("Interest rate", i)
    per_payment = installment * _timing_factor(i, timing)
    if is_zero(i):
        return pv / per_payment
    inside = 1 - pv * i / per_payment
    if inside <= 0:
        raise CalculationError(
            "The installment is too small: it does not even cover the interest on the present value."
        )
    return -math.log(inside) / math.log(1 + i)


# --------------------------------------------------------------------------
# Interest rate (numerical)
# --------------------------------------------------------------------------

def _solve_monotonic(f: Callable[[float], float], target: float, increasing: bool) -> float:
    """Find i with f(i) = target by bisection. ``f`` must be monotonic in i.

    Bisection is slow compared with Newton's method but it always converges
    once the answer is bracketed, which makes it easy to trust and to test.
    """
    lo, hi = -0.99, 1.0
    sign = 1 if increasing else -1

    def g(x: float) -> float:
        try:
            value = f(x)
        except OverflowError:  # both annuity factors blow up towards +infinity
            value = math.inf
        return sign * (value - target)

    while g(hi) < 0:  # widen the bracket upwards for very high rates
        hi *= 2
        if hi > 1e6:
            raise CalculationError("No interest rate below 100 000 000% gives this value.")
    if g(lo) > 0:
        raise CalculationError("No interest rate above -99% gives this value.")

    for _ in range(200):
        mid = (lo + hi) / 2
        if g(mid) < 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-15:
            break
    return (lo + hi) / 2


def rate_from_fv(fv: float, installment: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """Periodic rate i such that X * s_n(i) = FV  (replaces Excel P30 / R30, D13)."""
    require_positive("Future value", fv)
    require_positive("Installment", installment)
    require_positive("Number of payments", n)
    return _solve_monotonic(lambda i: accumulation_factor(i, n, timing), fv / installment, increasing=True)


def rate_from_pv(pv: float, installment: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """Periodic rate i such that X * a_n(i) = PV  (replaces Excel P31 / R31, D13)."""
    require_positive("Present value", pv)
    require_positive("Installment", installment)
    require_positive("Number of payments", n)
    return _solve_monotonic(lambda i: discount_factor(i, n, timing), pv / installment, increasing=False)


# --------------------------------------------------------------------------
# Everything on the sheet at once
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class AnnuityResults:
    """All outputs for one timing. A value is ``None`` when it cannot be
    calculated; the reason is then stored in ``errors[field_name]``."""

    timing: Timing
    future_value: float | None
    present_value: float | None
    years_from_fv: float | None
    years_from_pv: float | None
    installment_from_fv: float | None
    installment_from_pv: float | None
    rate_from_fv: float | None
    rate_from_pv: float | None
    errors: dict[str, str]


def _attempt(errors: dict[str, str], name: str, func: Callable[[], float]) -> float | None:
    try:
        return func()
    except CalculationError as exc:
        errors[name] = str(exc)
        return None
    except (ZeroDivisionError, OverflowError, ValueError):
        errors[name] = "Cannot be calculated for these inputs."
        return None


def annuity_summary(
    *,
    installment: float,
    rate: float,
    years: float,
    periods_per_year: float,
    pv: float,
    fv: float,
    timing: Timing,
) -> AnnuityResults:
    """Every output of '3. ANNUITIES' for one timing (column P or R)."""
    p = require_positive("Periods per year", periods_per_year)
    n = require_positive("Years", years) * p  # number of payments (Excel Q9*Q10)
    errors: dict[str, str] = {}
    return AnnuityResults(
        timing=Timing(timing),
        future_value=_attempt(errors, "future_value", lambda: future_value(installment, rate, n, timing)),
        present_value=_attempt(errors, "present_value", lambda: present_value(installment, rate, n, timing)),
        years_from_fv=_attempt(errors, "years_from_fv", lambda: term_from_fv(fv, installment, rate, timing) / p),
        years_from_pv=_attempt(errors, "years_from_pv", lambda: term_from_pv(pv, installment, rate, timing) / p),
        installment_from_fv=_attempt(errors, "installment_from_fv", lambda: installment_from_fv(fv, rate, n, timing)),
        installment_from_pv=_attempt(errors, "installment_from_pv", lambda: installment_from_pv(pv, rate, n, timing)),
        rate_from_fv=_attempt(errors, "rate_from_fv", lambda: rate_from_fv(fv, installment, n, timing)),
        rate_from_pv=_attempt(errors, "rate_from_pv", lambda: rate_from_pv(pv, installment, n, timing)),
        errors=errors,
    )
