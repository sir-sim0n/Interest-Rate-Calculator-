import pytest

from calculator.common import Timing
from calculator.increasing_annuities import (
    RetirementInputs,
    geometric_future_value,
    geometric_installment_from_pv,
    geometric_present_value,
    plan_retirement,
    stepped_future_value,
    stepped_installment_from_fv,
)

ARR, ADV = Timing.ARREARS, Timing.ADVANCE


def brute_geometric_fv(x, i, j, n, timing):
    shift = 0 if timing is ARR else 1
    return sum(x * (1 + j) ** (k - 1) * (1 + i) ** (n - k + shift) for k in range(1, n + 1))


def brute_stepped_fv(x, i, j, k, m, timing):
    n, shift = k * m, (0 if timing is ARR else 1)
    return sum(x * (1 + j) ** ((t - 1) // k) * (1 + i) ** (n - t + shift) for t in range(1, n + 1))


@pytest.mark.parametrize("timing", list(Timing))
@pytest.mark.parametrize("i,j", [(0.02, 0.05), (0.01, 0.005), (0.03, 0.03)])  # includes i = j
def test_geometric_matches_cash_flow_sum(timing, i, j):
    assert geometric_future_value(1000, i, j, 40, timing) == pytest.approx(brute_geometric_fv(1000, i, j, 40, timing))


@pytest.mark.parametrize("timing", list(Timing))
def test_stepped_matches_cash_flow_sum(timing):
    assert stepped_future_value(10_000, 0.02, 0.05, 4, 10, timing) == pytest.approx(
        brute_stepped_fv(10_000, 0.02, 0.05, 4, 10, timing))


def test_stepped_limit_when_block_growth_equals_inflation():
    i, k = 0.01, 12
    j = (1 + i) ** k - 1
    assert stepped_future_value(100, i, j, k, 5) == pytest.approx(brute_stepped_fv(100, i, j, k, 5, ARR))


def test_workbook_part1_values():
    assert stepped_future_value(10_000, 0.02, 0.05, 4, 10) == pytest.approx(736000.567643157, rel=1e-12)
    assert stepped_installment_from_fv(800_000, 0.02, 0.05, 4, 10) == pytest.approx(10869.556834198973)
    assert geometric_present_value(10_000, 0.02, 0.05, 40) == pytest.approx(729447.8035778366)
    assert geometric_installment_from_pv(400_000, 0.02, 0.05, 40, ADV) == pytest.approx(5376.078464032998)


def test_retirement_plan_matches_workbook_and_balances():
    inp = RetirementInputs(rate=0.0075, inflation=0.06, lump_sum=15_000, lump_sum_periods_per_year=12,
                           lump_sum_years=40, contribution_k=12, contribution_m=40,
                           first_withdrawal_today=4_000, years_to_inflate=40, withdrawal_k=12, withdrawal_m=20)
    res = plan_retirement(inp)
    assert res.first_contribution == pytest.approx(686.1994856, rel=1e-8)
    # The contributions plus the lump sum must exactly fund the withdrawals at retirement.
    contributions_fv = brute_stepped_fv(res.first_contribution, 0.0075, 0.06, 12, 40, ARR)
    assert contributions_fv + res.lump_sum_fv == pytest.approx(res.withdrawals_pv)
