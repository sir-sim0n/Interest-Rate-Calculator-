"""Export The Easy Broker data from the workbook into CSV files.

Reads BACKROOM2_TEB (company lists, share prices and country return bands)
and writes:

    calculator/data/companies.csv        country, exchange, company, price_usd
    calculator/data/country_returns.csv  country, low, high

Run from the project root:   python tools/export_market_data.py
"""

from __future__ import annotations

import csv
import re
import sys
import warnings
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "reference" / "INTEREST-RATE-CALCULATOR-48581275.xlsx"
DATA_DIR = ROOT / "calculator" / "data"

EXCHANGE_NAMES = {
    "JSE": "Johannesburg Stock Exchange",
    "FSE": "Frankfurt Stock Exchange",
    "Nasdaq": "Nasdaq",
    "TSE": "Tokyo Stock Exchange",
    "MOEX": "Moscow Exchange",
    "BM": "B3 / BM&FBovespa (São Paulo)",
    "SSE": "Shanghai Stock Exchange",
    "LSE": "London Stock Exchange",
}

# Excel names had to be valid range names, so spaces were removed.
DISPLAY_OVERRIDES = {
    "Industrial&CommercialBankofChina": "Industrial and Commercial Bank of China",
    "BancodoBrasil": "Banco do Brasil",
    "ItaúUnibanco": "Itaú Unibanco",
    "HSBCHoldings": "HSBC Holdings",
    "GlaxoSmithKline": "GlaxoSmithKline",
    "FirstRandLimited": "FirstRand Limited",
    "MercedesBenz": "Mercedes-Benz",
}


def display_name(excel_name: str) -> str:
    if excel_name in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[excel_name]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", excel_name)


def main() -> int:
    warnings.filterwarnings("ignore")
    wb = openpyxl.load_workbook(WORKBOOK, data_only=False)
    ws = wb["BACKROOM2_TEB"]

    # Price lookup: row 18 = company names, row 19 = prices (USD)
    prices = {}
    for col in range(1, ws.max_column + 1):
        name = ws.cell(18, col).value
        if name:
            prices[name] = float(ws.cell(19, col).value)

    # Table2 (A1:H12) countries, Table3 (K1:R12) exchanges: same column order
    rows = []
    for offset in range(8):
        country = ws.cell(1, 1 + offset).value
        exchange = ws.cell(1, 11 + offset).value
        for r in range(2, 13):
            company = ws.cell(r, 1 + offset).value
            if not company:
                continue
            assert ws.cell(r, 11 + offset).value == company, "country and exchange lists differ"
            rows.append({
                "country": display_name(country),
                "country_excel": country,
                "exchange": exchange,
                "exchange_name": EXCHANGE_NAMES[exchange],
                "company": display_name(company),
                "company_excel": company,
                "price_usd": prices[company],
            })

    bands = []
    for r in range(28, 36):
        country = ws.cell(r, 1).value
        formula = ws.cell(r, 3).value  # e.g. =RAND()*0.05+0.2
        m = re.fullmatch(r"=RAND\(\)\*([\d.]+)\+([\d.]+)", formula.replace(" ", ""))
        width, low = float(m.group(1)), float(m.group(2))
        bands.append({
            "country": display_name(country),
            "country_excel": country,
            "low": low,
            "high": round(low + width, 10),
            "label": ws.cell(r, 2).value,
        })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for filename, data in (("companies.csv", rows), ("country_returns.csv", bands)):
        with open(DATA_DIR / filename, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
        print(f"wrote {len(data):>3} rows -> {DATA_DIR / filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
