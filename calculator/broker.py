"""The Easy Broker ('TEB' + 'BACKROOM2_TEB').

A share-purchase calculator:

    cost in USD = shares x price per share                 TEB!I8 / I18
    cost in ZAR = cost in USD x USD/ZAR exchange rate       TEB!I9 / I19
    value after n years = cost in ZAR x (1 + r)^n           TEB!I26

``r`` is a *simulated* annual return drawn uniformly from the country's
historical band (Excel: ``RAND()*width + low`` in BACKROOM2_TEB!C28:C35).

Differences from Excel (validation / robustness, not financial logic):
* Share prices are looked up directly, so the three companies whose Excel
  range names did not match ("MTN Group", "Absa Group Limited",
  "Industrial&CommercialBankofChina") now work, and prices never go stale.
* The random draw takes an explicit ``random.Random`` so results can be
  reproduced (and tested); the app has a "re-roll" button instead of Excel
  recalculating RAND() on every edit.
* The USD/ZAR rate defaults to the workbook's last saved value; it can be
  edited or fetched live (Excel needed a Microsoft 365 linked data type).
"""

from __future__ import annotations

import csv
import json
import random
import urllib.request
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from .common import CalculationError, require_non_negative, require_positive

DATA_DIR = Path(__file__).resolve().parent / "data"

DEFAULT_USD_ZAR = 17.9954          # BACKROOM2_TEB!B23, last refreshed by Excel
DEFAULT_USD_ZAR_DATE = date(2024, 8, 22)
LIVE_FX_URL = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=ZAR"

# The simulated returns saved in the workbook (BACKROOM2_TEB!C28:C35). The app
# starts with these so its first screen reproduces the workbook; users can
# then draw new ones.
WORKBOOK_RETURNS = {
    "South Africa": 0.23877545500305564,
    "Germany": 0.2451629221066175,
    "USA": 0.08557030218644512,
    "Japan": 0.20988616748431096,
    "Russia": 0.017661116422336552,
    "Brazil": 0.1649793968627249,
    "China": 0.12039348165738746,
    "UK": 0.1003441231541588,
}


@dataclass(frozen=True)
class Company:
    name: str
    country: str
    exchange: str
    exchange_name: str
    price_usd: float
    excel_name: str


@dataclass(frozen=True)
class ReturnBand:
    country: str
    low: float
    high: float
    label: str


class MarketData:
    """The company list and return bands from ``calculator/data/*.csv``."""

    def __init__(self, companies: list[Company], bands: list[ReturnBand]):
        self.companies = companies
        self.bands = {b.country: b for b in bands}

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "MarketData":
        with open(data_dir / "companies.csv", encoding="utf-8", newline="") as fh:
            companies = [
                Company(
                    name=row["company"],
                    country=row["country"],
                    exchange=row["exchange"],
                    exchange_name=row["exchange_name"],
                    price_usd=float(row["price_usd"]),
                    excel_name=row["company_excel"],
                )
                for row in csv.DictReader(fh)
            ]
        with open(data_dir / "country_returns.csv", encoding="utf-8", newline="") as fh:
            bands = [
                ReturnBand(row["country"], float(row["low"]), float(row["high"]), row["label"])
                for row in csv.DictReader(fh)
            ]
        return cls(companies, bands)

    def countries(self) -> list[str]:
        return list(dict.fromkeys(c.country for c in self.companies))

    def exchanges(self) -> list[str]:
        return list(dict.fromkeys(c.exchange for c in self.companies))

    def companies_in_country(self, country: str) -> list[Company]:
        return [c for c in self.companies if c.country == country]

    def companies_on_exchange(self, exchange: str) -> list[Company]:
        return [c for c in self.companies if c.exchange == exchange]

    def company(self, name: str) -> Company:
        for c in self.companies:
            if name in (c.name, c.excel_name):
                return c
        raise CalculationError(f"Unknown company: {name}")

    def band(self, country: str) -> ReturnBand:
        try:
            return self.bands[country]
        except KeyError:
            raise CalculationError(f"No return band for {country}") from None


@lru_cache(maxsize=1)
def market_data() -> MarketData:
    """Load the CSV data once per process."""
    return MarketData.load()


# --------------------------------------------------------------------------
# Calculations
# --------------------------------------------------------------------------

def purchase_cost_usd(price_usd: float, shares: float) -> float:
    """TEB!I8 = shares x price."""
    return require_non_negative("Number of shares", shares) * require_non_negative("Share price", price_usd)


def to_zar(amount_usd: float, usd_zar: float) -> float:
    """TEB!I9 = USD amount x USD/ZAR."""
    return amount_usd * require_positive("USD/ZAR exchange rate", usd_zar)


def sample_return(band: ReturnBand, rng: random.Random) -> float:
    """One simulated annual return: uniform on [low, high)  (Excel RAND()*width + low)."""
    return band.low + (band.high - band.low) * rng.random()


def sample_all_returns(data: MarketData, rng: random.Random) -> dict[str, float]:
    """A return for every country (BACKROOM2_TEB!C28:C35, Excel Chart 2)."""
    return {country: sample_return(band, rng) for country, band in data.bands.items()}


def projected_value(cost_zar: float, annual_return: float, years: float) -> float:
    """TEB!I26 = cost x (1 + r)^n."""
    require_non_negative("Years", years)
    if annual_return <= -1:
        raise CalculationError("The annual return must be greater than -100%.")
    return cost_zar * (1 + annual_return) ** years


def fetch_live_usd_zar(timeout: float = 5.0) -> tuple[float, str]:
    """Latest USD/ZAR reference rate (European Central Bank data via the free
    Frankfurter API). Returns ``(rate, date)``; raises CalculationError when
    offline so the app can fall back to the default."""
    try:
        # The API rejects Python's default User-Agent, so send a normal one.
        request = urllib.request.Request(LIVE_FX_URL, headers={"User-Agent": "interest-rate-calculator/1.0",
                                                               "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
        return float(payload["rates"]["ZAR"]), str(payload["date"])
    except Exception as exc:  # network errors, bad JSON, missing keys
        raise CalculationError(f"Could not fetch a live exchange rate ({exc.__class__.__name__}).") from exc
