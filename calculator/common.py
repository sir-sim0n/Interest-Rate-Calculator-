"""Shared building blocks used by every calculator module.

* ``RateType``  - the five ways an interest rate can be quoted (the Excel
  dropdown lists in BACKROOM1!A8:A12 / B7:F7 and '2. SINGLE INVESTMENTS'!K14).
* ``Timing``    - payments in arrears (end of period) or in advance (start).
* ``CalculationError`` - raised instead of returning Excel's ``#NUM!``,
  ``#DIV/0!``, ``"ERROR"`` or ``"-"`` values.
* Small validation helpers so each formula can check its inputs in one line.
"""

from __future__ import annotations

import math
from enum import Enum


class CalculationError(ValueError):
    """A calculation cannot be performed for the given inputs.

    The message is written for the end user (the Streamlit pages display it
    as-is), e.g. "The installment is too small to cover the interest".
    """


class RateType(str, Enum):
    """How an interest rate is quoted.

    Notation follows BWIA 111:

    ==================  ==========  ==================================================
    Member              Symbol      Meaning
    ==================  ==========  ==================================================
    EFFECTIVE_ANNUAL    i           compound rate per year
    EFFECTIVE_PERIODIC  i(p)/p      compound rate per 1/p of a year
    NOMINAL             i(p)        annual rate convertible p times a year
    SIMPLE              r           simple (non-compounding) rate per period
    CONTINUOUS          delta       force of interest (compounded continuously)
    ==================  ==========  ==================================================
    """

    EFFECTIVE_ANNUAL = "Effective annual"
    EFFECTIVE_PERIODIC = "Effective periodic"
    NOMINAL = "Nominal"
    SIMPLE = "Simple"
    CONTINUOUS = "Continuous"

    @property
    def symbol(self) -> str:
        return {
            RateType.EFFECTIVE_ANNUAL: "i",
            RateType.EFFECTIVE_PERIODIC: "i(p)/p",
            RateType.NOMINAL: "i(p)",
            RateType.SIMPLE: "r",
            RateType.CONTINUOUS: "δ",
        }[self]


class Timing(str, Enum):
    """When level payments are made within each period."""

    ARREARS = "Arrears"  # end of each period (annuity-immediate)
    ADVANCE = "Advance"  # start of each period (annuity-due)


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------

def require_finite(name: str, value: float) -> float:
    if value is None or not math.isfinite(value):
        raise CalculationError(f"{name} must be a number.")
    return float(value)


def require_positive(name: str, value: float) -> float:
    value = require_finite(name, value)
    if value <= 0:
        raise CalculationError(f"{name} must be greater than zero.")
    return value


def require_non_negative(name: str, value: float) -> float:
    value = require_finite(name, value)
    if value < 0:
        raise CalculationError(f"{name} cannot be negative.")
    return value


def require_rate(name: str, value: float) -> float:
    """A compound rate must be greater than -100% so that 1 + i > 0."""
    value = require_finite(name, value)
    if value <= -1:
        raise CalculationError(f"{name} must be greater than -100%.")
    return value


def is_zero(value: float, tol: float = 1e-12) -> bool:
    """True when a rate is so close to zero that the i = 0 limit must be used."""
    return abs(value) < tol
