"""Generate docs/validation_report.md from the Excel parity comparisons.

Run from the project root:   python tools/generate_validation_report.py
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validation.excel_parity import (  # noqa: E402
    REL_TOL,
    Comparison,
    PythonError,
    _is_number,
    all_comparisons,
    load_fixture,
)
from validation.known_discrepancies import REGISTRY  # noqa: E402

OUTPUT = ROOT / "docs" / "validation_report.md"

MODULE_TITLES = {
    "rate_converter_grid1": "1. Rate converter (grid 1)",
    "rate_converter_grid2": "2. Single investments – embedded converter (grid 2)",
    "rate_converter_grid3": "3. Annuities – embedded converter (grid 3)",
    "rate_converter_grid4": "4. Loans – embedded converter (grid 4)",
    "rate_converter_grid5": "5. Increasing annuities – embedded converter (grid 5)",
    "single_investment": "2. Single investments",
    "annuities": "3. Annuities",
    "loans": "4. Loans",
    "increasing_annuities": "5. Increasing annuities – part 1",
    "retirement": "5. Increasing annuities – part 2 (retirement plan)",
    "broker": "TEB – The Easy Broker",
}


def fmt(value) -> str:
    if isinstance(value, PythonError):
        return "error: " + str(value)
    if _is_number(value):
        if value == int(value) and abs(value) < 1e15:
            return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:g}"
        return f"{value:,.10g}" if abs(value) >= 1000 else f"{value:.10g}"
    return f"`{value}`" if value is not None else "(blank)"


def rel_diff(a, b) -> float | None:
    if _is_number(a) and _is_number(b):
        scale = max(abs(a), abs(b))
        return 0.0 if scale == 0 else abs(a - b) / scale
    return None


def status_label(row: Comparison) -> str:
    return {"match": "match", "known": f"**{row.defect}**", "FAIL": "**FAIL**"}[row.status]


def main() -> int:
    rows = all_comparisons()
    by_source = defaultdict(list)
    for r in rows:
        by_source[r.source].append(r)

    lines: list[str] = []
    add = lines.append
    add("# Validation report: Python vs the Excel workbook")
    add("")
    add(f"Generated {date.today().isoformat()} by `tools/generate_validation_report.py`. "
        "The same comparisons run as tests in `tests/test_excel_parity.py`.")
    add("")
    add("## How the comparison works")
    add("")
    add("- Excel's saved values: every output of every sheet at the inputs the workbook was saved with, "
        "exactly as Microsoft Excel calculated them.")
    add(f"- Recalculated scenarios: {len({r.scenario for r in by_source['libreoffice']})} extra scenarios, written "
        "into copies of the workbook and recalculated from its own formulas by "
        f"{load_fixture('excel_scenarios.json')['engine'].split(' (')[0]}. LibreOffice reproduced all 529 "
        "deterministic numeric cells of the original file exactly, so it stands in for Excel.")
    add(f"- A match means the values agree to a relative tolerance of {REL_TOL:g} (about 9 significant figures), "
        "or both sides report \"cannot be calculated\" (an Excel error such as `#NUM!` and a Python "
        "`CalculationError`), or both show `-` (not applicable).")
    add("- A known discrepancy is accepted only when three things hold: the cell is a registered defect; "
        "a bug-for-bug copy of Excel's formula reproduces Excel's value (so the cause is proven); and the "
        "Python value passes an independent check (a brute-force cash-flow sum, a period-by-period loop, "
        "or plugging the answer back in).")
    add("")

    # Summary ---------------------------------------------------------------
    add("## Summary")
    add("")
    add("| Reference | Outputs compared | Match | Known discrepancy | Unexplained |")
    add("|---|---:|---:|---:|---:|")
    for source, title in (("excel", "Excel saved values"), ("libreoffice", "Recalculated scenarios")):
        c = Counter(r.status for r in by_source[source])
        add(f"| {title} | {len(by_source[source])} | {c['match']} | {c['known']} | {c['FAIL']} |")
    total = Counter(r.status for r in rows)
    add(f"| Total | {len(rows)} | {total['match']} | {total['known']} | {total['FAIL']} |")
    add("")
    diffs = [d for r in rows if r.status == "match" and (d := rel_diff(r.excel, r.python)) is not None]
    nonzero = [d for d in diffs if d > 0]
    add(f"Of the {len(diffs)} numeric matches, {len(diffs) - len(nonzero)} are bit-for-bit identical. The largest "
        f"relative difference is {max(diffs):.1e}, which is floating-point rounding: Python and Excel apply the "
        "same operations in a slightly different order, e.g. `ln(x)/ln(y)` instead of Excel's `LOG(x, y)`, or "
        "converting through the effective annual rate.")
    add("")

    # By module ---------------------------------------------------------------
    add("## Results by module")
    add("")
    add("| Module | Outputs | Match | Known discrepancy | Defects seen |")
    add("|---|---:|---:|---:|---|")
    by_module = defaultdict(list)
    for r in rows:
        by_module[r.module].append(r)
    for module, title in MODULE_TITLES.items():
        group = by_module.get(module, [])
        c = Counter(r.status for r in group)
        defects = sorted({r.defect for r in group if r.defect}, key=lambda d: int(d[1:]))
        add(f"| {title} | {len(group)} | {c['match']} | {c['known']} | {', '.join(defects) or '–'} |")
    add("")

    # Defect register -------------------------------------------------------------
    add("## Discrepancy register")
    add("")
    add("| ID | Where | Problem | Excel computes | Python computes | Times seen |")
    add("|---|---|---|---|---|---:|")
    seen = Counter(r.defect for r in rows if r.status == "known")
    for d in REGISTRY.values():
        count = seen.get(d.id, 0)
        shown = str(count) if count else "not numeric (see note)"
        add(f"| {d.id} | {d.sheet} | {d.title} | {d.excel} | {d.python} | {shown} |")
    add("")
    add("D17 and D18 are about workbook behaviour rather than a formula's value:")
    add("- D17: dropdowns copy a value, so the chosen value goes stale. In the saved workbook, "
        "`3. ANNUITIES!Q8` = 2.0201% no longer equals either option (7% or 0.6689%). The Python app always uses "
        "the live selection.")
    add("- D18: in The Easy Broker, three companies cannot be priced in Excel because their range names don't "
        "match. Python looks them up directly, and `tests/test_broker_and_dates.py` checks all three.")
    add("")
    add("Some defective formulas give the right answer for particular inputs, e.g. every D5 cell when "
        "Years = 1, or D1 when p = 12. Those cases are counted as matches:")
    add("")
    silent = Counter(r.note.split(" is in")[0] for r in rows if r.status == "match" and r.note)
    add(", ".join(f"{k}: {v}" for k, v in sorted(silent.items(), key=lambda kv: int(kv[0][1:]))) or "none")
    add("")

    # One example per defect --------------------------------------------------------
    add("## One example of each discrepancy")
    add("")
    add("| ID | Scenario | Cell | Excel | Python | How Python was checked |")
    add("|---|---|---|---:|---:|---|")
    examples = {}
    for r in rows:
        if r.status == "known":
            examples.setdefault(r.defect, r)
    for defect in sorted(examples, key=lambda d: int(d[1:])):
        r = examples[defect]
        how = r.note.split("Python checked: ")[-1]
        add(f"| {r.defect} | {r.scenario} | `{r.cell}` | {fmt(r.excel)} | {fmt(r.python)} | {how} |")
    add("")

    # Level 1 full table --------------------------------------------------------------
    add("## Excel's saved values, output by output")
    add("")
    add("| Scenario | Output | Cell | Excel | Python | Result |")
    add("|---|---|---|---:|---:|---|")
    for r in by_source["excel"]:
        add(f"| {r.module} | {r.output} | `{r.cell}` | {fmt(r.excel)} | {fmt(r.python)} | {status_label(r)} |")
    add("")

    # Level 2 discrepancy rows ---------------------------------------------------------
    add("## Recalculated scenarios: every discrepancy")
    add("")
    add("All other recalculated outputs matched. The full list of discrepancies is below.")
    add("")
    add("<details><summary>Show all "
        f"{sum(1 for r in by_source['libreoffice'] if r.status != 'match')} rows</summary>")
    add("")
    add("| Scenario | Output | Cell | Excel | Python | Defect |")
    add("|---|---|---|---:|---:|---|")
    for r in by_source["libreoffice"]:
        if r.status != "match":
            add(f"| {r.scenario} | {r.output} | `{r.cell}` | {fmt(r.excel)} | {fmt(r.python)} | {status_label(r)} |")
    add("")
    add("</details>")
    add("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}  ({len(rows)} comparisons, {total['FAIL']} unexplained)")
    return 1 if total["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
