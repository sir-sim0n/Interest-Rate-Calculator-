"""Amortising loans ('4.LOANS' + BACKROOM1!AM38:AQ44).

A loan of ``L`` is repaid by level installments ``X`` at a rate ``i`` per
period, ``p`` payments per year. The key quantity is the **outstanding
balance** after ``t`` payments (retrospective method):

    arrears:  B_t = L(1+i)^t - X * s_t
    advance:  B_t = L(1+i)^t - X * s̈_t      (value at time t, before payment t+1,
                                             exactly as in Excel U29)

Every other output follows from B_t:

* interest in the next payment (t+1): i * B_t (arrears); d * B_t (advance), d = i/(1+i)
* capital in the next payment:        X - interest
* number of payments needed:          smallest N with X * a_N >= L
* last (smaller) payment:             what is left after N - 1 full payments
* interest / capital paid in year T:  cumulative interest at T*p minus at (T-1)*p

Here ``T`` is a year number and ``t = T * p`` the matching payment number, as
in Excel's helper cells '4.LOANS'!Q18:R20.

Differences from Excel (see docs/validation_report.md):
* D14 Excel uses the arrears formula for the advance "payments needed".
* D15 Excel's advance interest component is B_t * i instead of B_t * d.
* D16 Excel's "Balance after T+1" is (years x last payment - X), which has no
  financial meaning; here it is the balance at year T + 1.
* New (not in Excel): year-T totals for advance loans, warnings, and a full
  amortisation schedule (replacing the unused leftover tables).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .annuities import accumulation_factor, discount_factor
from .common import (
    CalculationError,
    Timing,
    is_zero,
    require_non_negative,
    require_positive,
    require_rate,
)


def _check(principal: float, installment: float | None, rate: float) -> None:
    require_positive("Loan amount", principal)
    if installment is not None:
        require_positive("Installment", installment)
    require_rate("Interest rate", rate)


# --------------------------------------------------------------------------
# Installment and loan amount
# --------------------------------------------------------------------------

def installment(principal: float, rate: float, n_payments: float, timing: Timing = Timing.ARREARS) -> float:
    """Level installment that repays ``principal``: X = L / a_n  (Excel P27 / U27)."""
    _check(principal, None, rate)
    return principal / discount_factor(rate, require_positive("Number of payments", n_payments), timing)


def loan_amount(installment_: float, rate: float, n_payments: float, timing: Timing = Timing.ARREARS) -> float:
    """Loan that ``installment_`` can repay: L = X * a_n  (Excel P28 / U28)."""
    require_positive("Installment", installment_)
    return installment_ * discount_factor(rate, require_positive("Number of payments", n_payments), timing)


# --------------------------------------------------------------------------
# Balance and the split of a payment into interest and capital
# --------------------------------------------------------------------------

def balance(principal: float, installment_: float, rate: float, t: float, timing: Timing = Timing.ARREARS) -> float:
    """Outstanding balance at time ``t`` after ``t`` payments  (Excel P29 / U29)."""
    _check(principal, installment_, rate)
    require_non_negative("Payment number", t)
    return principal * (1 + rate) ** t - installment_ * accumulation_factor(rate, t, timing)


def _balance_just_after_payment(principal: float, installment_: float, rate: float, t: float, timing: Timing) -> float:
    """Balance immediately after the t-th payment has been made."""
    if Timing(timing) is Timing.ARREARS:
        return balance(principal, installment_, rate, t, timing)
    if t == 0:
        return principal  # advance: nothing has been paid yet at time 0
    # advance: the t-th payment is made at time t-1, one period before Excel's B_t
    return balance(principal, installment_, rate, t, timing) / (1 + rate)


def interest_in_payment(principal: float, installment_: float, rate: float, t: float, timing: Timing = Timing.ARREARS) -> float:
    """Interest component of payment number ``t + 1``  (Excel P30 / U30, D15).

    Interest in a payment is always i x (balance just after the previous payment).
    For arrears that is i * B_t. For advance it is d * B_t, and 0 for the very
    first payment, which is made on day one before any interest has accrued.
    """
    if Timing(timing) is Timing.ADVANCE and t == 0:
        _check(principal, installment_, rate)
        return 0.0
    return rate * _balance_just_after_payment(principal, installment_, rate, t, timing)


def capital_in_payment(principal: float, installment_: float, rate: float, t: float, timing: Timing = Timing.ARREARS) -> float:
    """Capital component of payment number ``t + 1``: X - interest  (Excel P31 / U31)."""
    return installment_ - interest_in_payment(principal, installment_, rate, t, timing)


def cumulative_interest(principal: float, installment_: float, rate: float, t: float, timing: Timing = Timing.ARREARS) -> float:
    """Total interest contained in the first ``t`` payments.

    = amount paid - capital repaid = t*X - (L - balance just after payment t).
    For arrears this equals Excel's (L*i - X) * s_t + t*X  (BACKROOM1!AM43).
    """
    remaining = _balance_just_after_payment(principal, installment_, rate, t, timing)
    return t * installment_ - (principal - remaining)


@dataclass(frozen=True)
class YearTotals:
    interest: float
    capital: float


def year_totals(
    principal: float, installment_: float, rate: float, year: float, periods_per_year: float,
    timing: Timing = Timing.ARREARS,
) -> YearTotals:
    """Interest and capital paid during year ``year`` (payments (T-1)p+1 ... Tp).

    Excel P34 / P35 (arrears only): AM44 - AN44 and AM43 - AN43.
    """
    p = require_positive("Periods per year", periods_per_year)
    if year < 1:
        raise CalculationError("The year T must be at least 1.")
    end, start = year * p, (year - 1) * p
    interest = (cumulative_interest(principal, installment_, rate, end, timing)
                - cumulative_interest(principal, installment_, rate, start, timing))
    return YearTotals(interest=interest, capital=(end - start) * installment_ - interest)


# --------------------------------------------------------------------------
# Term and last payment
# --------------------------------------------------------------------------

def payments_needed_exact(principal: float, installment_: float, rate: float, timing: Timing = Timing.ARREARS) -> float:
    """Solve X * a_n = L for n (may be fractional).

    arrears: n = -ln(1 - L*i/X) / ln(1+i)        (Excel P32)
    advance: n = -ln(1 - L*d/X) / ln(1+i)        (Excel U32 reuses arrears, D14)
    """
    _check(principal, installment_, rate)
    if is_zero(rate):
        return principal / installment_
    per_period_interest = principal * rate if Timing(timing) is Timing.ARREARS else principal * rate / (1 + rate)
    if installment_ <= per_period_interest:
        raise CalculationError(
            "The installment is too small to cover the interest, so the loan is never repaid."
        )
    return -math.log(1 - per_period_interest / installment_) / math.log(1 + rate)


def payments_needed(principal: float, installment_: float, rate: float, timing: Timing = Timing.ARREARS) -> int:
    """Whole number of payments needed: Excel ROUNDUP(n, 0).

    A tolerance of 1e-9 stops floating-point noise (e.g. 12.000000000001)
    from adding an extra payment.
    """
    return max(1, math.ceil(payments_needed_exact(principal, installment_, rate, timing) - 1e-9))


def last_payment(principal: float, installment_: float, rate: float, timing: Timing = Timing.ARREARS) -> float:
    """Size of the final (reduced) payment  (Excel P33 / U33).

    After N - 1 full payments the remaining balance plus one period's interest
    is paid off: arrears B_(N-1) * (1+i); advance B_(N-1) (Excel's advance B
    already includes that period's interest).
    """
    n = payments_needed(principal, installment_, rate, timing)
    remaining = balance(principal, installment_, rate, n - 1, timing)
    return remaining * (1 + rate) if Timing(timing) is Timing.ARREARS else remaining


def total_interest(principal: float, installment_: float, n_payments: float) -> float:
    """n * X - L  (Excel P36 / U36). Only meaningful when X repays the loan in n payments."""
    return n_payments * installment_ - principal


# --------------------------------------------------------------------------
# Amortisation schedule (new)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ScheduleRow:
    payment_number: int
    time_years: float
    opening_balance: float
    payment: float
    interest: float
    capital: float
    closing_balance: float


def amortisation_schedule(
    principal: float,
    installment_: float,
    rate: float,
    periods_per_year: float,
    timing: Timing = Timing.ARREARS,
    max_payments: int | None = None,
) -> list[ScheduleRow]:
    """Period-by-period schedule, built by simple iteration (no closed forms).

    Because it is computed step by step, the schedule is also used in the
    tests as an independent check of the closed-form formulas above.
    The final payment is reduced so the balance ends at exactly zero. If the
    installment never repays the loan, the schedule stops after
    ``max_payments`` rows (default 600) with the balance still outstanding.
    """
    _check(principal, installment_, rate)
    p = require_positive("Periods per year", periods_per_year)
    limit = max_payments if max_payments is not None else 600
    advance = Timing(timing) is Timing.ADVANCE

    rows: list[ScheduleRow] = []
    outstanding = principal
    for k in range(1, limit + 1):
        # Interest accrues on the balance over the period before this payment.
        interest = 0.0 if (advance and k == 1) else outstanding * rate
        payment = min(installment_, outstanding + interest)
        capital = payment - interest
        closing = outstanding - capital
        rows.append(ScheduleRow(
            payment_number=k,
            time_years=(k - 1) / p if advance else k / p,
            opening_balance=outstanding,
            payment=payment,
            interest=interest,
            capital=capital,
            closing_balance=closing,
        ))
        outstanding = closing
        if outstanding <= 1e-9 * principal:
            break
    return rows


# --------------------------------------------------------------------------
# Everything on the sheet at once
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class LoanResults:
    """All outputs for one timing. ``None`` values have a reason in ``errors``."""

    timing: Timing
    installment: float | None
    loan_amount: float | None
    balance_at_T: float | None
    interest_next_payment: float | None
    capital_next_payment: float | None
    payments_needed: int | None
    last_payment: float | None
    capital_in_year_T: float | None
    interest_in_year_T: float | None
    total_interest: float | None
    balance_at_T_plus_1: float | None
    errors: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _attempt(errors: dict[str, str], name: str, func):
    try:
        return func()
    except CalculationError as exc:
        errors[name] = str(exc)
    except (ZeroDivisionError, OverflowError, ValueError):
        errors[name] = "Cannot be calculated for these inputs."
    return None


def loan_summary(
    *,
    principal: float,
    installment_: float,
    rate: float,
    years: float,
    periods_per_year: float,
    year_T: float,
    timing: Timing,
) -> LoanResults:
    """Every output of '4.LOANS' for one timing (column P = arrears, U = advance)."""
    p = require_positive("Periods per year", periods_per_year)
    n = require_positive("Number of years", years) * p      # BACKROOM1!AM38
    t = require_non_negative("Year T", year_T) * p          # '4.LOANS'!R18
    errors: dict[str, str] = {}

    totals = _attempt(errors, "year_totals", lambda: year_totals(principal, installment_, rate, year_T, p, timing))
    if totals is None:
        errors["capital_in_year_T"] = errors["interest_in_year_T"] = errors.pop("year_totals")
    split_interest = _attempt(errors, "interest_next_payment",
                              lambda: interest_in_payment(principal, installment_, rate, t, timing))

    warnings: list[str] = []
    per_period_interest = principal * rate if Timing(timing) is Timing.ARREARS else principal * rate / (1 + rate)
    if installment_ <= per_period_interest:
        warnings.append(
            f"The installment ({installment_:,.2f}) does not cover the interest on the loan "
            f"({per_period_interest:,.2f} per period), so the balance grows instead of shrinking."
        )
    if abs(n - round(n)) > 1e-9:
        warnings.append(
            f"The term gives a fractional number of payments ({n:.2f}). The formulas still work, "
            "but a real loan would have a whole number of payments."
        )
    amortising = _attempt(errors, "installment", lambda: installment(principal, rate, n, timing))
    if amortising is not None and abs(amortising - installment_) > 0.005:
        warnings.append(
            f"Total interest assumes the installment repays the loan exactly in {n:g} payments; "
            f"that installment would be {amortising:,.2f}, not {installment_:,.2f}."
        )

    return LoanResults(
        timing=Timing(timing),
        installment=amortising,
        loan_amount=_attempt(errors, "loan_amount", lambda: loan_amount(installment_, rate, n, timing)),
        balance_at_T=_attempt(errors, "balance_at_T", lambda: balance(principal, installment_, rate, t, timing)),
        interest_next_payment=split_interest,
        capital_next_payment=None if split_interest is None else installment_ - split_interest,
        payments_needed=_attempt(errors, "payments_needed",
                                 lambda: payments_needed(principal, installment_, rate, timing)),
        last_payment=_attempt(errors, "last_payment", lambda: last_payment(principal, installment_, rate, timing)),
        capital_in_year_T=None if totals is None else totals.capital,
        interest_in_year_T=None if totals is None else totals.interest,
        total_interest=_attempt(errors, "total_interest", lambda: total_interest(principal, installment_, n)),
        balance_at_T_plus_1=_attempt(errors, "balance_at_T_plus_1",
                                     lambda: balance(principal, installment_, rate, t + p, timing)),
        errors=errors,
        warnings=warnings,
    )
