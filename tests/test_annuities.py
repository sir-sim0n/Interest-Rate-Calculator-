import pytest

from calculator.annuities import (
    accumulation_factor,
    annuity_summary,
    discount_factor,
    future_value,
    installment_from_fv,
    installment_from_pv,
    present_value,
    rate_from_fv,
    rate_from_pv,
    term_from_fv,
    term_from_pv,
)
from calculator.common import CalculationError, Timing

ARR, ADV = Timing.ARREARS, Timing.ADVANCE


def test_textbook_factors():
    # a_10 and s_10 at 5% (standard actuarial tables)
    assert discount_factor(0.05, 10) == pytest.approx(7.721734929, rel=1e-9)
    assert accumulation_factor(0.05, 10) == pytest.approx(12.57789254, rel=1e-9)


def test_advance_is_arrears_times_one_plus_i():
    assert discount_factor(0.05, 10, ADV) == pytest.approx(1.05 * discount_factor(0.05, 10))
    assert accumulation_factor(0.05, 10, ADV) == pytest.approx(1.05 * accumulation_factor(0.05, 10))


def test_zero_interest_limit():
    assert accumulation_factor(0.0, 12) == 12
    assert discount_factor(0.0, 12, ADV) == 12


@pytest.mark.parametrize("timing", list(Timing))
def test_future_value_equals_sum_of_payments(timing):
    i, n, x = 0.015, 24, 700
    shift = 0 if timing is ARR else 1
    brute = sum(x * (1 + i) ** (n - k + shift) for k in range(1, n + 1))
    assert future_value(x, i, n, timing) == pytest.approx(brute, rel=1e-12)


def test_excel_fv_bracket_bug_is_fixed():
    # Workbook sample: X = 5000, i = 2.0201% per month, 60 payments
    assert future_value(5000, 0.020201340026755776, 60) == pytest.approx(574248.2725560901, rel=1e-12)


@pytest.mark.parametrize("timing", list(Timing))
def test_installment_term_and_rate_invert_values(timing):
    i, n, x = 0.01, 36, 250
    fv, pv = future_value(x, i, n, timing), present_value(x, i, n, timing)
    assert installment_from_fv(fv, i, n, timing) == pytest.approx(x)
    assert installment_from_pv(pv, i, n, timing) == pytest.approx(x)
    assert term_from_fv(fv, x, i, timing) == pytest.approx(n)
    assert term_from_pv(pv, x, i, timing) == pytest.approx(n)
    assert rate_from_fv(fv, x, n, timing) == pytest.approx(i, abs=1e-12)
    assert rate_from_pv(pv, x, n, timing) == pytest.approx(i, abs=1e-12)


def test_rate_solver_textbook_case():
    assert rate_from_pv(7721.734929, 1000, 10) == pytest.approx(0.05, abs=1e-9)


def test_installment_too_small_for_present_value():
    with pytest.raises(CalculationError):
        term_from_pv(10000, 100, 0.02)  # interest alone is 200 per period


def test_summary_collects_errors_instead_of_crashing():
    res = annuity_summary(installment=100, rate=0.02, years=5, periods_per_year=12, pv=10000, fv=7000,
                          timing=ARR)
    assert res.years_from_pv is None and "too small" in res.errors["years_from_pv"]
    assert res.future_value is not None
