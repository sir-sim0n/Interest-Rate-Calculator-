"""The closed-form loan formulas are checked against a period-by-period schedule."""

import pytest

from calculator.common import CalculationError, Timing
from calculator.loans import (
    amortisation_schedule,
    balance,
    cumulative_interest,
    installment,
    interest_in_payment,
    last_payment,
    loan_amount,
    loan_summary,
    payments_needed,
    total_interest,
    year_totals,
)

ARR, ADV = Timing.ARREARS, Timing.ADVANCE
L, X, I, P = 250_000, 8_500, 0.005, 12  # the loan shown in the PowerPoint


def test_textbook_installment():
    assert installment(100_000, 0.01, 12) == pytest.approx(8884.878868, rel=1e-9)
    assert loan_amount(8884.878868, 0.01, 12) == pytest.approx(100_000, rel=1e-9)


@pytest.mark.parametrize("timing", list(Timing))
def test_schedule_matches_closed_forms(timing):
    rows = amortisation_schedule(L, X, I, P, timing)
    n = payments_needed(L, X, I, timing)
    assert len(rows) == n
    assert rows[-1].closing_balance == pytest.approx(0, abs=1e-6)
    assert rows[-1].payment == pytest.approx(last_payment(L, X, I, timing))
    for t in (0, 1, 12, 20):
        # interest in payment t+1
        assert rows[t].interest == pytest.approx(interest_in_payment(L, X, I, t, timing))
        # cumulative interest in the first t payments
        assert sum(r.interest for r in rows[:t]) == pytest.approx(cumulative_interest(L, X, I, t, timing), abs=1e-6)


def test_balance_arrears_equals_schedule_closing_balance():
    rows = amortisation_schedule(L, X, I, P, ARR)
    assert balance(L, X, I, 24, ARR) == pytest.approx(rows[23].closing_balance)


def test_balance_advance_is_value_at_time_t_before_next_payment():
    rows = amortisation_schedule(L, X, I, P, ADV)
    # after 24 payments (made at times 0..23) the balance accrues one period to time 24
    assert balance(L, X, I, 24, ADV) == pytest.approx(rows[23].closing_balance * (1 + I))


def test_advance_first_payment_has_no_interest():
    assert interest_in_payment(L, X, I, 0, ADV) == 0.0


@pytest.mark.parametrize("timing", list(Timing))
def test_year_totals_match_schedule(timing):
    rows = amortisation_schedule(L, X, I, P, timing)
    totals = year_totals(L, X, I, 2, P, timing)   # payments 13-24, well inside the term
    year2 = rows[12:24]
    assert totals.interest == pytest.approx(sum(r.interest for r in year2))
    assert totals.capital == pytest.approx(sum(r.capital for r in year2))


def test_total_interest_for_exact_installment_equals_schedule():
    x = installment(L, I, 72)
    rows = amortisation_schedule(L, x, I, P, ARR)
    assert total_interest(L, x, 72) == pytest.approx(sum(r.interest for r in rows))


def test_installment_below_interest_never_repays():
    with pytest.raises(CalculationError):
        payments_needed(250_000, 10_000, 0.06)


def test_summary_warns_about_workbook_sample():
    res = loan_summary(principal=250_000, installment_=10_000, rate=0.06, years=7.7315068493150685,
                       periods_per_year=2, year_T=2, timing=ARR)
    assert res.payments_needed is None
    assert any("does not cover the interest" in w for w in res.warnings)
    assert res.balance_at_T == pytest.approx(271_873.08, rel=1e-9)
