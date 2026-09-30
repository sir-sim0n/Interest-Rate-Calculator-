"""Term of an investment/loan measured between two dates.

Excel: every sheet has a "START DATE / END DATE" block with separate month,
year and day cells, combined with ``DATE(year, month, day)``, and the term is

    years = (end_date - start_date) / 365          e.g. '2. SINGLE INVESTMENTS'!E9

That is the *Actual/365 Fixed* day-count convention: actual days elapsed,
always divided by 365 (leap days are not adjusted). The same convention is
kept here so results match the workbook.

Differences from Excel (validation, not financial logic):
* Python ``date`` objects reject impossible dates such as 31 February,
  whereas Excel's DATE() silently rolls them into the next month.
* An end date before the start date raises an error instead of returning a
  negative number of years.
"""

from __future__ import annotations

from datetime import date

from .common import CalculationError

DAYS_PER_YEAR = 365  # Actual/365 Fixed, as in the workbook


def years_between(start: date, end: date) -> float:
    """Number of years from ``start`` to ``end`` using Actual/365."""
    if end < start:
        raise CalculationError("The end date must be on or after the start date.")
    return (end - start).days / DAYS_PER_YEAR
