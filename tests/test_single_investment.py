import math

import pytest

from calculator.common import CalculationError, RateType
from calculator.single_investment import (
    Outcome,
    compare_interest_types,
    future_value,
    growth_table,
    interest_earned,
    present_value,
    solve,
    solve_rate,
    solve_years,
)

EA, EP, NOM, SIM, CON = list(RateType)


def test_textbook_future_values():
    assert future_value(1000, 0.10, EA, 2) == pytest.approx(1210)
    assert future_value(1000, 0.05, SIM, 3, periods_per_year=1) == pytest.approx(1150)
    assert future_value(1000, 0.12, NOM, 1, periods_per_year=12) == pytest.approx(1000 * 1.01 ** 12)
    assert future_value(1000, 0.01, EP, 1, periods_per_year=12) == pytest.approx(1000 * 1.01 ** 12)
    assert future_value(1000, 0.05, CON, 2) == pytest.approx(1000 * math.exp(0.1))


def test_workbook_sample_simple_future_value():
    # '2. SINGLE INVESTMENTS' as shipped: PV 2000, 10% simple per period, 8 periods, 10 years
    assert solve(Outcome.FUTURE_VALUE, SIM, pv=2000, fv=10000, rate=0.1, years=10, periods_per_year=8) == 18000


def test_present_value_is_inverse_of_future_value():
    for t in RateType:
        fv = future_value(2500, 0.06, t, 7, 4)
        assert present_value(fv, 0.06, t, 7, 4) == pytest.approx(2500)


@pytest.mark.parametrize("rtype", list(RateType))
def test_solve_years_and_rate_invert_future_value(rtype):
    fv = future_value(2000, 0.08, rtype, 6.5, 4)
    assert solve_years(2000, fv, 0.08, rtype, 4) == pytest.approx(6.5)
    assert solve_rate(2000, fv, 6.5, rtype, 4) == pytest.approx(0.08)


def test_effective_annual_rate_fixes_excel_precedence_bug():
    # Excel D9 gives (5)^(8/10) - 1 = 262.39 %; correct answer is 5^(1/10) - 1
    assert solve_rate(2000, 10000, 10, EA, 8) == pytest.approx(5 ** 0.1 - 1)


def test_interest_earned_is_fv_minus_pv():
    # Excel D8 would give 18000 - 1111.11 = 16888.89
    assert interest_earned(2000, 0.1, SIM, 10, 8) == pytest.approx(16000)
    # Excel D10 gives 0 for continuous
    assert interest_earned(1000, 0.05, CON, 2) == pytest.approx(1000 * (math.exp(0.1) - 1))


def test_compare_interest_types_has_all_five():
    assert len(compare_interest_types(1000, 0.05, 3, 12)) == 5


def test_growth_table_includes_fractional_final_year():
    rows = growth_table(1000, 0.1, EA, 2.5)
    assert [r.year for r in rows] == [0, 1, 2, 2.5]
    assert rows[0].value == 1000 and rows[-1].value == pytest.approx(1000 * 1.1 ** 2.5)


def test_invalid_inputs_raise():
    with pytest.raises(CalculationError):
        solve_years(0, 1000, 0.1, EA)
    with pytest.raises(CalculationError):
        solve_years(1000, 2000, 0.0, EA)
    with pytest.raises(CalculationError):
        future_value(1000, 0.1, EA, 1, periods_per_year=0)
