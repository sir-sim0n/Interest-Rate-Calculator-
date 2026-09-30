import random
import urllib.request
from datetime import date

import pytest

from calculator import broker
from calculator.common import CalculationError
from calculator.dates import years_between


def test_market_data_matches_workbook_structure():
    data = broker.market_data()
    assert len(data.companies) == 50
    assert len(data.countries()) == 8 and len(data.exchanges()) == 8
    assert {c.exchange for c in data.companies_in_country("South Africa")} == {"JSE"}


@pytest.mark.parametrize("name", ["MTN Group", "Absa Group Limited", "Industrial&CommercialBankofChina"])
def test_companies_broken_in_excel_can_be_looked_up(name):
    assert broker.market_data().company(name).price_usd > 0


def test_workbook_sample_costs():
    usd = broker.purchase_cost_usd(29, 6)
    zar = broker.to_zar(usd, broker.DEFAULT_USD_ZAR)
    assert (usd, zar) == (174, pytest.approx(3131.1996))
    assert broker.projected_value(zar, 0.12039348165738746, 5) == pytest.approx(5527.9438138453315)


def test_simulated_return_is_in_band_and_reproducible():
    band = broker.market_data().band("USA")
    draws = [broker.sample_return(band, random.Random(7)) for _ in range(2)]
    assert draws[0] == draws[1] and band.low <= draws[0] < band.high


def test_fx_rate_must_be_positive():
    with pytest.raises(CalculationError):
        broker.to_zar(100, 0)


def test_live_fx_failure_is_reported(monkeypatch):
    def offline(*args, **kwargs):
        raise OSError("offline")
    monkeypatch.setattr(urllib.request, "urlopen", offline)
    with pytest.raises(CalculationError):
        broker.fetch_live_usd_zar()


def test_years_between_uses_actual_365():
    # '2. SINGLE INVESTMENTS'!E9
    assert years_between(date(2010, 1, 26), date(2024, 5, 7)) == pytest.approx(14.287671232876713, rel=1e-15)
    with pytest.raises(CalculationError):
        years_between(date(2024, 1, 2), date(2024, 1, 1))
