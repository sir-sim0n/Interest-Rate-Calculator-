"""Financial engine of the Interest Rate Calculator.

Pure Python (standard library only) and independent of the user interface,
so every function can be imported in a notebook, a script or the tests:

>>> from calculator import rates, RateType
>>> round(rates.convert_rate(0.12, RateType.NOMINAL, RateType.EFFECTIVE_ANNUAL, from_periods=12), 6)
0.126825

Modules map one-to-one onto the workbook's sheets:

=====================  ==================================
Module                 Excel sheet
=====================  ==================================
rates                  1. RATE CONVERTER (+ embedded converters)
single_investment      2. SINGLE INVESTMENTS
annuities              3. ANNUITIES
loans                  4.LOANS
increasing_annuities   5. INCREASING ANNUITIES
broker                 TEB (The Easy Broker)
dates                  the START/END DATE blocks
=====================  ==================================
"""

from .common import CalculationError, RateType, Timing

__all__ = ["CalculationError", "RateType", "Timing"]
