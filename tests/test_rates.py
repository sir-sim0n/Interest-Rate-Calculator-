import math
from itertools import product

import pytest

from calculator.common import CalculationError, RateType
from calculator.rates import convert_rate, equivalent_rates, from_effective_annual, to_effective_annual

EA, EP, NOM, SIM, CON = list(RateType)


# Textbook values -------------------------------------------------------------

def test_nominal_monthly_to_effective_annual():
    # i(12) = 12%  ->  i = (1.01)^12 - 1
    assert convert_rate(0.12, NOM, EA, from_periods=12) == pytest.approx(0.1268250301, rel=1e-9)


def test_effective_annual_to_nominal_quarterly():
    assert convert_rate(0.08, EA, NOM, to_periods=4) == pytest.approx(4 * (1.08 ** 0.25 - 1), rel=1e-12)


def test_effective_annual_to_force_of_interest():
    assert convert_rate(0.10, EA, CON) == pytest.approx(math.log(1.1), rel=1e-12)


def test_continuous_to_effective_annual():
    assert convert_rate(0.05, CON, EA) == pytest.approx(math.exp(0.05) - 1, rel=1e-12)


def test_effective_periodic_to_effective_periodic_changes_frequency():
    # Excel sample on '2. SINGLE INVESTMENTS': 7% per month -> per quarter = 1.07^3 - 1
    assert convert_rate(0.07, EP, EP, from_periods=12, to_periods=4) == pytest.approx(0.225043, rel=1e-9)


def test_simple_rate_is_per_period_and_equivalence_depends_on_term():
    # 5% simple per period, 2 periods a year, over 1 year: 1 + 0.05*2 = 1.10
    assert to_effective_annual(0.05, SIM, periods_per_year=2, years=1) == pytest.approx(0.10)
    # over 3 years: 1 + 0.05*2*3 = 1.30 = (1+i)^3
    assert to_effective_annual(0.05, SIM, periods_per_year=2, years=3) == pytest.approx(1.3 ** (1 / 3) - 1)
    assert from_effective_annual(1.3 ** (1 / 3) - 1, SIM, periods_per_year=2, years=3) == pytest.approx(0.05)


def test_same_type_returns_rate_unchanged():
    assert convert_rate(0.0831, NOM, NOM, from_periods=4, to_periods=4) == 0.0831


# Properties ------------------------------------------------------------------

@pytest.mark.parametrize("src,dst", list(product(RateType, RateType)))
@pytest.mark.parametrize("pf,pt,nf,nt", [(1, 1, 1, 1), (4, 12, 1, 1), (12, 2, 5, 3), (2, 52, 10, 10)])
def test_round_trip(src, dst, pf, pt, nf, nt):
    forward = convert_rate(0.07, src, dst, pf, pt, nf, nt)
    back = convert_rate(forward, dst, src, pt, pf, nt, nf)
    assert back == pytest.approx(0.07, rel=1e-10)


def test_equivalent_rates_covers_all_types():
    table = equivalent_rates(0.1, EA, to_periods=12)
    assert set(table) == set(RateType)
    assert table[EA] == 0.1


# Invalid input ---------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [dict(from_periods=0), dict(to_periods=-1)])
def test_periods_must_be_positive(kwargs):
    with pytest.raises(CalculationError):
        convert_rate(0.1, NOM, EA, **{"from_periods": 1, "to_periods": 1, **kwargs})


def test_rate_must_exceed_minus_100_percent():
    with pytest.raises(CalculationError):
        convert_rate(-1.0, EA, NOM)
