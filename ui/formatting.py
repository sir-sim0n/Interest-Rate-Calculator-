"""Display formats (match the workbook's number formats)."""

from __future__ import annotations

DASH = "–"


def money(value: float | None, symbol: str = "R", decimals: int = 2) -> str:
    """R 18,000.00 / -R 6,312.38 (Excel: [$R-1C09] #,##0.00)."""
    if value is None:
        return DASH
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol} {abs(value):,.{decimals}f}"


def usd(value: float | None) -> str:
    return money(value, "$")


def pct(value: float | None, decimals: int = 4) -> str:
    """0.0824 -> 8.2432%."""
    if value is None:
        return DASH
    return f"{value * 100:,.{decimals}f}%"


def num(value: float | None, decimals: int = 4) -> str:
    if value is None:
        return DASH
    return f"{value:,.{decimals}f}"


def years(value: float | None) -> str:
    return DASH if value is None else f"{value:,.4f} years"
