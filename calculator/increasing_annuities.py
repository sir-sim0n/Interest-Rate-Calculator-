"""Increasing annuities and the retirement plan ('5. INCREASING ANNUITIES').

Part 1 has two kinds of increasing annuity, each in arrears and in advance.

1. **Every payment increasing** (geometric, the formula in the project PDF).
   Payments X, X(1+j), X(1+j)^2, ... for n = N*P periods at rate i:

       FV = X * ((1+i)^n - (1+j)^n) / (i - j)           Excel K25 (arrears)
       PV = FV / (1+i)^n                                 Excel K26

   When i = j the fraction becomes 0/0; its limit n(1+i)^(n-1) is used
   (Excel shows #DIV/0!).

2. **Every k-th payment increasing** (stepped). Payments stay at X for k
   periods, then increase by (1+j) for the next k periods, for m blocks:

       FV = X * s_k * ((1+i)^(k*m) - (1+j)^m) / ((1+i)^k - (1+j))   Excel E25
       PV = FV / (1+i)^(k*m)                                          Excel E26

   Each block of k level payments is worth X*s_k at its end, and those m
   block values grow geometrically by (1+j) while money grows by (1+i)^k.

Advance versions multiply by (1 + i). Installments "given FV/PV" divide the
target by the same factors. Part 1 has no Excel defects.

Part 2 (retirement plan) is ``plan_retirement``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .annuities import accumulation_factor
from .common import CalculationError, Timing, require_positive, require_rate


def _advance(i: float, timing: Timing) -> float:
    return (1 + i) if Timing(timing) is Timing.ADVANCE else 1.0


# --------------------------------------------------------------------------
# Every payment increasing (geometric)
# --------------------------------------------------------------------------

def geometric_fv_factor(i: float, j: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """FV of payments 1, (1+j), (1+j)^2, ... over n periods."""
    require_rate("Interest rate", i)
    require_rate("Growth rate", j)
    require_positive("Number of payments", n)
    if abs(i - j) < 1e-12:
        factor = n * (1 + i) ** (n - 1)  # limit as j -> i
    else:
        factor = ((1 + i) ** n - (1 + j) ** n) / (i - j)
    return factor * _advance(i, timing)


def geometric_future_value(payment: float, i: float, j: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """Excel K25 (arrears) / M25 (advance)."""
    return payment * geometric_fv_factor(i, j, n, timing)


def geometric_present_value(payment: float, i: float, j: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """Excel K26 / M26."""
    return geometric_future_value(payment, i, j, n, timing) / (1 + i) ** n


def geometric_installment_from_fv(fv: float, i: float, j: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """First payment needed to accumulate ``fv``. Excel K23 / M23."""
    return fv / geometric_fv_factor(i, j, n, timing)


def geometric_installment_from_pv(pv: float, i: float, j: float, n: float, timing: Timing = Timing.ARREARS) -> float:
    """First payment with present value ``pv``. Excel K24 / M24."""
    return pv * (1 + i) ** n / geometric_fv_factor(i, j, n, timing)


# --------------------------------------------------------------------------
# Every k-th payment increasing (stepped)
# --------------------------------------------------------------------------

def stepped_growth_factor(i: float, j: float, k: float, m: float) -> float:
    """((1+i)^(k*m) - (1+j)^m) / ((1+i)^k - (1+j))  = BACKROOM1!AY7 / AZ7.

    This is sum over blocks b = 0..m-1 of (1+j)^b * (1+i)^(k*(m-1-b)).
    When (1+i)^k = 1+j the fraction is 0/0 and its limit m*(1+i)^(k*(m-1)) is used.
    """
    require_rate("Interest rate", i)
    require_rate("Growth rate", j)
    require_positive("Payments per block (k)", k)
    require_positive("Number of blocks (m)", m)
    block_growth = (1 + i) ** k
    if abs(block_growth - (1 + j)) < 1e-12:
        return m * block_growth ** (m - 1)
    return (block_growth ** m - (1 + j) ** m) / (block_growth - (1 + j))


def stepped_fv_factor(i: float, j: float, k: float, m: float, timing: Timing = Timing.ARREARS) -> float:
    """FV of a stepped annuity whose first payment is 1."""
    return accumulation_factor(i, k, timing) * stepped_growth_factor(i, j, k, m)


def stepped_future_value(payment: float, i: float, j: float, k: float, m: float, timing: Timing = Timing.ARREARS) -> float:
    """Excel E25 (arrears) / G25 (advance)."""
    return payment * stepped_fv_factor(i, j, k, m, timing)


def stepped_present_value(payment: float, i: float, j: float, k: float, m: float, timing: Timing = Timing.ARREARS) -> float:
    """Excel E26 / G26."""
    return stepped_future_value(payment, i, j, k, m, timing) / (1 + i) ** (k * m)


def stepped_installment_from_fv(fv: float, i: float, j: float, k: float, m: float, timing: Timing = Timing.ARREARS) -> float:
    """Excel E23 / G23."""
    return fv / stepped_fv_factor(i, j, k, m, timing)


def stepped_installment_from_pv(pv: float, i: float, j: float, k: float, m: float, timing: Timing = Timing.ARREARS) -> float:
    """Excel E24 / G24."""
    return pv * (1 + i) ** (k * m) / stepped_fv_factor(i, j, k, m, timing)


# --------------------------------------------------------------------------
# Part 1 summary
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class IncreasingAnnuityResults:
    installment_from_fv: float
    installment_from_pv: float
    future_value: float
    present_value: float


def stepped_summary(*, payment, rate, growth, k, m, pv, fv, timing) -> IncreasingAnnuityResults:
    """Excel D23:G26 (every k-th payment increasing)."""
    return IncreasingAnnuityResults(
        installment_from_fv=stepped_installment_from_fv(fv, rate, growth, k, m, timing),
        installment_from_pv=stepped_installment_from_pv(pv, rate, growth, k, m, timing),
        future_value=stepped_future_value(payment, rate, growth, k, m, timing),
        present_value=stepped_present_value(payment, rate, growth, k, m, timing),
    )


def geometric_summary(*, payment, rate, growth, years, periods_per_year, pv, fv, timing) -> IncreasingAnnuityResults:
    """Excel J23:M26 (every payment increasing), n = N * P  (I10 * I11)."""
    n = require_positive("Years", years) * require_positive("Periods per year", periods_per_year)
    return IncreasingAnnuityResults(
        installment_from_fv=geometric_installment_from_fv(fv, rate, growth, n, timing),
        installment_from_pv=geometric_installment_from_pv(pv, rate, growth, n, timing),
        future_value=geometric_future_value(payment, rate, growth, n, timing),
        present_value=geometric_present_value(payment, rate, growth, n, timing),
    )


# --------------------------------------------------------------------------
# Part 2: relationship between investments and withdrawals
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RetirementInputs:
    """Inputs of '5. INCREASING ANNUITIES'!J36:K42.

    One periodic rate and one inflation rate are shared by both columns,
    exactly as in Excel (K37 = J37, K38 = J38).
    """

    rate: float                       # J37  i per period (usually from the converter, G41)
    inflation: float                  # J38  j per block (per year when k = payments per year)
    lump_sum: float                   # J36  single investment made today
    lump_sum_periods_per_year: float  # J39  p
    lump_sum_years: float             # J40  n
    contribution_k: float             # J41  payments per level block (e.g. 12 = monthly, rising yearly)
    contribution_m: float             # J42  number of blocks (years of contributions)
    first_withdrawal_today: float     # K36  first withdrawal in today's money
    years_to_inflate: float           # K40  years until the first withdrawal
    withdrawal_k: float               # K41
    withdrawal_m: float               # K42  years of withdrawals


@dataclass(frozen=True)
class RetirementResult:
    first_withdrawal: float          # N36  = BACKROOM1!BM12
    withdrawals_fv: float            # N37  = BK18
    withdrawals_pv: float            # N38  = BK19 (value at retirement)
    lump_sum_fv: float               # N39  = BM5
    first_contribution: float        # N40  = BK20


def plan_retirement(inp: RetirementInputs) -> RetirementResult:
    """How large must the first (inflation-linked) contribution be?

    1. Inflate the first withdrawal to retirement:  W1 = W0 (1+j)^years
    2. Value the stepped withdrawals at retirement: PV_w = W1 * FVfactor / (1+i)^(k*m)
    3. Grow the lump sum to retirement:             C (1+i)^(p*n)
    4. Contributions must cover the gap at retirement:
           x * s_k * G(i, j, k_c, m_c) = PV_w - lump sum FV
    """
    i, j = inp.rate, inp.inflation
    first_withdrawal = inp.first_withdrawal_today * (1 + j) ** inp.years_to_inflate
    withdrawals_fv = stepped_future_value(first_withdrawal, i, j, inp.withdrawal_k, inp.withdrawal_m)
    withdrawals_pv = withdrawals_fv / (1 + i) ** (inp.withdrawal_k * inp.withdrawal_m)
    lump_sum_fv = inp.lump_sum * (1 + i) ** (inp.lump_sum_periods_per_year * inp.lump_sum_years)
    contribution_factor = stepped_fv_factor(i, j, inp.contribution_k, inp.contribution_m)
    if contribution_factor == 0:
        raise CalculationError("The contribution period must be longer than zero.")
    return RetirementResult(
        first_withdrawal=first_withdrawal,
        withdrawals_fv=withdrawals_fv,
        withdrawals_pv=withdrawals_pv,
        lump_sum_fv=lump_sum_fv,
        first_contribution=(withdrawals_pv - lump_sum_fv) / contribution_factor,
    )
