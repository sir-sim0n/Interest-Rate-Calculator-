"""Python vs the Excel workbook, output by output.

Two references are used (see validation/excel_parity.py):
* ``excel``       - the values Microsoft Excel saved in the workbook;
* ``libreoffice`` - 180+ extra input scenarios recalculated from the
  workbook's own formulas by LibreOffice.

Every output must either match within floating-point tolerance, or be a
registered defect whose Excel value is reproduced by the defective formula
and whose Python value passes an independent check.
"""

from collections import Counter

import pytest

from validation.excel_parity import all_comparisons
from validation.known_discrepancies import REGISTRY

COMPARISONS = all_comparisons()


def test_fixtures_are_present():
    sources = Counter(c.source for c in COMPARISONS)
    assert sources["excel"] >= 60, "run tools/extract_excel_reference.py"
    assert sources["libreoffice"] >= 900, "run tools/build_excel_scenarios.py"


@pytest.mark.parametrize("row", COMPARISONS, ids=lambda r: f"{r.source}:{r.scenario}:{r.output}")
def test_output_matches_excel_or_is_an_explained_defect(row):
    assert row.status != "FAIL", (
        f"{row.cell}: Excel={row.excel!r} Python={row.python!r} - {row.note}")


def test_every_numeric_defect_is_demonstrated():
    seen = {c.defect for c in COMPARISONS if c.status == "known"}
    numeric = {f"D{n}" for n in range(1, 17)}  # D17/D18 are behavioural, not numeric
    assert numeric <= seen, f"not demonstrated by any scenario: {sorted(numeric - seen)}"
    assert seen <= set(REGISTRY)
