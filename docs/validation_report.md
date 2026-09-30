# Validation report: Python vs the Excel workbook

Generated 2026-09-30 by `tools/generate_validation_report.py`. The same comparisons run as tests in `tests/test_excel_parity.py`.

## How the comparison works

- Excel's saved values: every output of every sheet at the inputs the workbook was saved with, exactly as Microsoft Excel calculated them.
- Recalculated scenarios: 593 extra scenarios, written into copies of the workbook and recalculated from its own formulas by LibreOffice 26.2.5.2 620(Build:2). LibreOffice reproduced all 529 deterministic numeric cells of the original file exactly, so it stands in for Excel.
- A match means the values agree to a relative tolerance of 1e-09 (about 9 significant figures), or both sides report "cannot be calculated" (an Excel error such as `#NUM!` and a Python `CalculationError`), or both show `-` (not applicable).
- A known discrepancy is accepted only when three things hold: the cell is a registered defect; a bug-for-bug copy of Excel's formula reproduces Excel's value (so the cause is proven); and the Python value passes an independent check (a brute-force cash-flow sum, a period-by-period loop, or plugging the answer back in).

## Summary

| Reference | Outputs compared | Match | Known discrepancy | Unexplained |
|---|---:|---:|---:|---:|
| Excel saved values | 69 | 58 | 11 | 0 |
| Recalculated scenarios | 987 | 771 | 216 | 0 |
| Total | 1056 | 829 | 227 | 0 |

Of the 671 numeric matches, 117 are bit-for-bit identical. The largest relative difference is 8.6e-13, which is floating-point rounding: Python and Excel apply the same operations in a slightly different order, e.g. `ln(x)/ln(y)` instead of Excel's `LOG(x, y)`, or converting through the effective annual rate.

## Results by module

| Module | Outputs | Match | Known discrepancy | Defects seen |
|---|---:|---:|---:|---|
| 1. Rate converter (grid 1) | 101 | 76 | 25 | D1, D2, D3, D4, D5 |
| 2. Single investments – embedded converter (grid 2) | 101 | 78 | 23 | D1, D2, D3, D4, D5 |
| 3. Annuities – embedded converter (grid 3) | 101 | 77 | 24 | D1, D2, D3, D4, D5 |
| 4. Loans – embedded converter (grid 4) | 101 | 69 | 32 | D1, D2, D3, D4, D5, D6 |
| 5. Increasing annuities – embedded converter (grid 5) | 101 | 67 | 34 | D1, D2, D3, D4, D5, D7 |
| 2. Single investments | 228 | 211 | 17 | D8, D9, D10 |
| 3. Annuities | 96 | 55 | 41 | D11, D12, D13 |
| 4. Loans | 133 | 102 | 31 | D14, D15, D16 |
| 5. Increasing annuities – part 1 | 64 | 64 | 0 | – |
| 5. Increasing annuities – part 2 (retirement plan) | 15 | 15 | 0 | – |
| TEB – The Easy Broker | 15 | 15 | 0 | – |

## Discrepancy register

| ID | Where | Problem | Excel computes | Python computes | Times seen |
|---|---|---|---|---|---:|
| D1 | Rate converters (all 5 grids) | Nominal → effective annual uses a fixed 12 | (1 + i(p)/p)^12 − 1 | (1 + i(p)/p)^p − 1 | 15 |
| D2 | Rate converters | → continuous raises the logarithm to a power | LN(1+i)^n (grids 1–5), and LN(1+i)^(n·p) for nominal (grids 1 and 5) | δ = ln(1 + i) | 11 |
| D3 | Rate converters | Continuous → effective annual returns a periodic rate | e^(δ/(n·p)) − 1 | e^δ − 1 | 16 |
| D4 | Rate converters | Continuous → continuous is missing | "ERROR" | δ (unchanged) | 20 |
| D5 | Rate converters | The term (Years) is used inconsistently | simple/continuous cells ignore Years in one direction and use it in the other | equivalence over n years: 1 + r·p·n = (1 + i)^n; identical to Excel when Years = 1 | 52 |
| D6 | Loans converter (grid 4) | Simple → periodic/nominal/simple reads blank cells | 0 | correct conversion | 12 |
| D7 | Increasing-annuities converter (grid 5) | Simple → periodic/nominal/simple is broken | #REF! | correct conversion | 12 |
| D8 | 2. SINGLE INVESTMENTS | Interest earned mixes two questions | FV(from PV) − PV(from FV) | FV(from PV) − PV | 12 |
| D9 | 2. SINGLE INVESTMENTS | Effective annual rate: operator precedence | (FV/PV)^(1/n·p) − 1, i.e. exponent p/n | (FV/PV)^(1/n) − 1 | 2 |
| D10 | 2. SINGLE INVESTMENTS | Interest earned (continuous) reads a blank cell | 0 | PV·(e^(δn) − 1) | 3 |
| D11 | 3. ANNUITIES | FV in arrears: misplaced bracket | (X(1+i)^n − 1)/i | X((1+i)^n − 1)/i | 6 |
| D12 | 3. ANNUITIES | Years in advance multiply by (1+i) instead of dividing | ln(1 + FV·i·(1+i)/X)/ln(1+i) | ln(1 + FV·i/(X(1+i)))/ln(1+i) | 11 |
| D13 | 3. ANNUITIES | "Interest" outputs are value ratios, not rates | e.g. (X(1+i)^n − 1)/FV | the rate i solving X·s_n(i) = FV (bisection) | 24 |
| D14 | 4.LOANS | Advance: payments needed uses the arrears formula | −ln(1 − L·i/X)/ln(1+i) | −ln(1 − L·d/X)/ln(1+i),  d = i/(1+i) | 10 |
| D15 | 4.LOANS | Advance: interest component uses i instead of d | B_t · i | B_t · d  (0 for the first payment) | 14 |
| D16 | 4.LOANS | "Balance after T+1" has no financial meaning | years × last payment − X | balance at year T + 1: L(1+i)^t' − X·s_t',  t' = (T+1)·p | 7 |
| D17 | 3. ANNUITIES / 4.LOANS / 2. SINGLE INVESTMENTS | Dropdowns copy a value, so the chosen rate/term goes stale | e.g. Q8 = 2.0201% matches neither option any more | the selected rate is always live | not numeric (see note) |
| D18 | TEB | Broken INDIRECT names, stale price copies, volatile RAND(), Excel-365-only FX | 3 companies unusable, results change on every edit | direct price lookup, seeded simulation, editable/live FX | not numeric (see note) |

D17 and D18 are about workbook behaviour rather than a formula's value:
- D17: dropdowns copy a value, so the chosen value goes stale. In the saved workbook, `3. ANNUITIES!Q8` = 2.0201% no longer equals either option (7% or 0.6689%). The Python app always uses the live selection.
- D18: in The Easy Broker, three companies cannot be priced in Excel because their range names don't match. Python looks them up directly, and `tests/test_broker_and_dates.py` checks all three.

Some defective formulas give the right answer for particular inputs, e.g. every D5 cell when Years = 1, or D1 when p = 12. Those cases are counted as matches:

D1: 5, D2: 17, D3: 5, D5: 156, D9: 1, D12: 1, D14: 4

## One example of each discrepancy

| ID | Scenario | Cell | Excel | Python | How Python was checked |
|---|---|---|---:|---:|---|
| D1 | rate_converter_grid1/A/NOMINAL->EFFECTIVE_ANNUAL | `1. RATE CONVERTER!O17` | 0.2682417946 | 0.08243216 | both rates give the same effective annual growth (growth-factor check) |
| D2 | rate_converter_grid1/A/NOMINAL->CONTINUOUS | `1. RATE CONVERTER!O17` | 3.508195095e-05 | 0.07921050918 | both rates give the same effective annual growth (growth-factor check) |
| D3 | rate_converter_grid3/as_shipped | `3. ANNUITIES!L17` | 0.006688938354 | 0.08328706767 | both rates give the same effective annual growth (growth-factor check) |
| D4 | rate_converter_grid1/A/CONTINUOUS->CONTINUOUS | `1. RATE CONVERTER!O17` | `ERROR` | 0.08 | both rates give the same effective annual growth (growth-factor check) |
| D5 | rate_converter_grid1/D/EFFECTIVE_ANNUAL->SIMPLE | `1. RATE CONVERTER!O17` | 0.005833333333 | 0.01875358333 | both rates give the same effective annual growth (growth-factor check) |
| D6 | rate_converter_grid4/A/SIMPLE->EFFECTIVE_PERIODIC | `4.LOANS!J17` | 0 | 0.0234056908 | both rates give the same effective annual growth (growth-factor check) |
| D7 | rate_converter_grid5/A/SIMPLE->EFFECTIVE_PERIODIC | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.0234056908 | both rates give the same effective annual growth (growth-factor check) |
| D8 | single_investment/S1/INTEREST_EARNED/EFFECTIVE_ANNUAL | `2. SINGLE INVESTMENTS!K16` | 1,332.052026 | 3,187.48492 | PV·((1 + i)^n − 1) with i from the rate converter |
| D9 | single_investment/S1/INTEREST_RATE/EFFECTIVE_ANNUAL | `2. SINGLE INVESTMENTS!K18` | 2.623898318 | 0.1746189431 | PV·(1 + rate)^n reproduces FV |
| D10 | single_investment/S1/INTEREST_EARNED/CONTINUOUS | `2. SINGLE INVESTMENTS!K16` | 0 | 3,436.563657 | PV·((1 + i)^n − 1) with i from the rate converter |
| D11 | annuities/as_shipped | `3. ANNUITIES!P24` | 821,707.1042 | 574,248.2726 | sum of every payment accumulated to the end |
| D12 | annuities/as_shipped | `3. ANNUITIES!R26` | 0.1118374547 | 0.1075083258 | X·s̈_n with this n reproduces FV |
| D13 | annuities/as_shipped | `3. ANNUITIES!P30` | 2.515088578 | -0.7575757576 | X·s_n at this rate reproduces FV |
| D14 | loans/L3 | `4.LOANS!U32` | 342 | 326 | period-by-period repayment loop |
| D15 | loans/as_shipped | `4.LOANS!U30` | 16,154.89862 | 15,240.4704 | period-by-period loop: interest accrued since the previous payment |
| D16 | loans/as_shipped | `4.LOANS!P37` | `#NUM!` | 284,876.5927 | period-by-period balance loop |

## Excel's saved values, output by output

| Scenario | Output | Cell | Excel | Python | Result |
|---|---|---|---:|---:|---|
| rate_converter_grid1 | converted_rate | `1. RATE CONVERTER!O17` | 0.08 | 0.08 | match |
| rate_converter_grid2 | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.225043 | 0.225043 | match |
| rate_converter_grid3 | converted_rate | `3. ANNUITIES!L17` | 0.006688938354 | 0.08328706767 | **D3** |
| rate_converter_grid4 | converted_rate | `4.LOANS!J17` | 0.030225 | 0.030225 | match |
| rate_converter_grid5 | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.0075 | 0.0075 | match |
| single_investment | answer | `2. SINGLE INVESTMENTS!K16` | 18,000 | 18,000 | match |
| single_investment | years_out | `2. SINGLE INVESTMENTS!K17` | `-` | `-` | match |
| single_investment | rate_out | `2. SINGLE INVESTMENTS!K18` | `-` | `-` | match |
| annuities | arrears.future_value | `3. ANNUITIES!P24` | 821,707.1042 | 574,248.2726 | **D11** |
| annuities | arrears.present_value | `3. ANNUITIES!P25` | 172,960.2559 | 172,960.2559 | match |
| annuities | arrears.years_from_fv | `3. ANNUITIES!P26` | 0.1096518075 | 0.1096518075 | match |
| annuities | arrears.years_from_pv | `3. ANNUITIES!P27` | 0.08847179843 | 0.08847179843 | match |
| annuities | arrears.installment_from_fv | `3. ANNUITIES!P28` | 57.46643321 | 57.46643321 | match |
| annuities | arrears.installment_from_pv | `3. ANNUITIES!P29` | 150.3235519 | 150.3235519 | match |
| annuities | arrears.rate_from_fv | `3. ANNUITIES!P30` | 2.515088578 | -0.7575757576 | **D13** |
| annuities | arrears.rate_from_pv | `3. ANNUITIES!P31` | 0.6719286424 | 0.9615384615 | **D13** |
| annuities | advance.future_value | `3. ANNUITIES!R24` | 585,848.8572 | 585,848.8572 | match |
| annuities | advance.present_value | `3. ANNUITIES!R25` | 176,454.2848 | 176,454.2848 | match |
| annuities | advance.years_from_fv | `3. ANNUITIES!R26` | 0.1118374547 | 0.1075083258 | **D12** |
| annuities | advance.years_from_pv | `3. ANNUITIES!R27` | 0.09027854852 | 0.08670158438 | **D12** |
| annuities | advance.installment_from_fv | `3. ANNUITIES!R28` | 56.32852159 | 56.32852159 | match |
| annuities | advance.installment_from_pv | `3. ANNUITIES!R29` | 147.3469461 | 147.3469461 | match |
| annuities | advance.rate_from_fv | `3. ANNUITIES!R30` | 1.79317151 | -0.4310344828 | **D13** |
| annuities | advance.rate_from_pv | `3. ANNUITIES!R31` | 0.6855025014 | 25 | **D13** |
| loans | arrears.installment | `4.LOANS!P27` | 25,259.24591 | 25,259.24591 | match |
| loans | arrears.loan_amount | `4.LOANS!P28` | 98,973.65936 | 98,973.65936 | match |
| loans | arrears.balance_at_T | `4.LOANS!P29` | 271,873.08 | 271,873.08 | match |
| loans | arrears.interest_next_payment | `4.LOANS!P30` | 16,312.3848 | 16,312.3848 | match |
| loans | arrears.capital_next_payment | `4.LOANS!P31` | -6,312.3848 | -6,312.3848 | match |
| loans | arrears.payments_needed | `4.LOANS!P32` | `#NUM!` | error: The installment is too small to cover the interest, so the loan is never repaid. | match |
| loans | arrears.last_payment | `4.LOANS!P33` | `#NUM!` | error: The installment is too small to cover the interest, so the loan is never repaid. | match |
| loans | arrears.capital_in_year_T | `4.LOANS!P34` | -11,573.08 | -11,573.08 | match |
| loans | arrears.interest_in_year_T | `4.LOANS!P35` | 31,573.08 | 31,573.08 | match |
| loans | arrears.total_interest | `4.LOANS!P36` | -95,369.86301 | -95,369.86301 | match |
| loans | arrears.balance_at_T_plus_1 | `4.LOANS!P37` | `#NUM!` | 284,876.5927 | **D16** |
| loans | advance.installment | `4.LOANS!U27` | 23,829.47727 | 23,829.47727 | match |
| loans | advance.loan_amount | `4.LOANS!U28` | 104,912.0789 | 104,912.0789 | match |
| loans | advance.balance_at_T | `4.LOANS!U29` | 269,248.3104 | 269,248.3104 | match |
| loans | advance.interest_next_payment | `4.LOANS!U30` | 16,154.89862 | 15,240.4704 | **D15** |
| loans | advance.capital_next_payment | `4.LOANS!U31` | -6,154.898624 | -5,240.4704 | **D15** |
| loans | advance.payments_needed | `4.LOANS!U32` | `#NUM!` | error: The installment is too small to cover the interest, so the loan is never repaid. | match |
| loans | advance.last_payment | `4.LOANS!U33` | `#NUM!` | error: The installment is too small to cover the interest, so the loan is never repaid. | match |
| loans | advance.total_interest | `4.LOANS!U36` | -95,369.86301 | -95,369.86301 | match |
| increasing_annuities | stepped.arrears.installment_from_fv | `5. INCREASING ANNUITIES!E23` | 10,869.55683 | 10,869.55683 | match |
| increasing_annuities | stepped.arrears.installment_from_pv | `5. INCREASING ANNUITIES!E24` | 12,000.20631 | 12,000.20631 | match |
| increasing_annuities | stepped.arrears.future_value | `5. INCREASING ANNUITIES!E25` | 736,000.5676 | 736,000.5676 | match |
| increasing_annuities | stepped.arrears.present_value | `5. INCREASING ANNUITIES!E26` | 333,327.6027 | 333,327.6027 | match |
| increasing_annuities | stepped.advance.installment_from_fv | `5. INCREASING ANNUITIES!G23` | 10,656.42827 | 10,656.42827 | match |
| increasing_annuities | stepped.advance.installment_from_pv | `5. INCREASING ANNUITIES!G24` | 11,764.90815 | 11,764.90815 | match |
| increasing_annuities | stepped.advance.future_value | `5. INCREASING ANNUITIES!G25` | 750,720.579 | 750,720.579 | match |
| increasing_annuities | stepped.advance.present_value | `5. INCREASING ANNUITIES!G26` | 339,994.1547 | 339,994.1547 | match |
| increasing_annuities | geometric.arrears.installment_from_fv | `5. INCREASING ANNUITIES!K23` | 4,966.939792 | 4,966.939792 | match |
| increasing_annuities | geometric.arrears.installment_from_pv | `5. INCREASING ANNUITIES!K24` | 5,483.600033 | 5,483.600033 | match |
| increasing_annuities | geometric.arrears.future_value | `5. INCREASING ANNUITIES!K25` | 1,610,649.683 | 1,610,649.683 | match |
| increasing_annuities | geometric.arrears.present_value | `5. INCREASING ANNUITIES!K26` | 729,447.8036 | 729,447.8036 | match |
| increasing_annuities | geometric.advance.installment_from_fv | `5. INCREASING ANNUITIES!M23` | 4,869.548815 | 4,869.548815 | match |
| increasing_annuities | geometric.advance.installment_from_pv | `5. INCREASING ANNUITIES!M24` | 5,376.078464 | 5,376.078464 | match |
| increasing_annuities | geometric.advance.future_value | `5. INCREASING ANNUITIES!M25` | 1,642,862.676 | 1,642,862.676 | match |
| increasing_annuities | geometric.advance.present_value | `5. INCREASING ANNUITIES!M26` | 744,036.7596 | 744,036.7596 | match |
| retirement | first_withdrawal | `5. INCREASING ANNUITIES!N36` | 41,142.87175 | 41,142.87175 | match |
| retirement | withdrawals_fv | `5. INCREASING ANNUITIES!N37` | 42,651,411.86 | 42,651,411.86 | match |
| retirement | withdrawals_pv | `5. INCREASING ANNUITIES!N38` | 7,097,742.782 | 7,097,742.782 | match |
| retirement | lump_sum_fv | `5. INCREASING ANNUITIES!N39` | 541,648.5307 | 541,648.5307 | match |
| retirement | first_contribution | `5. INCREASING ANNUITIES!N40` | 686.1994856 | 686.1994856 | match |
| broker | exchange_cost_usd | `TEB!I8` | 290 | 290 | match |
| broker | exchange_cost_zar | `TEB!I9` | 5,218.666 | 5,218.666 | match |
| broker | country_cost_usd | `TEB!I18` | 174 | 174 | match |
| broker | country_cost_zar | `TEB!I19` | 3,131.1996 | 3,131.1996 | match |
| broker | projected_value | `TEB!I26` | 5,527.943814 | 5,527.943814 | match |

## Recalculated scenarios: every discrepancy

All other recalculated outputs matched. The full list of discrepancies is below.

<details><summary>Show all 216 rows</summary>

| Scenario | Output | Cell | Excel | Python | Defect |
|---|---|---|---:|---:|---|
| rate_converter_grid1/A/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `1. RATE CONVERTER!O17` | 0.2682417946 | 0.08243216 | **D1** |
| rate_converter_grid2/A/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.2682417946 | 0.08243216 | **D1** |
| rate_converter_grid3/A/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `3. ANNUITIES!L17` | 0.2682417946 | 0.08243216 | **D1** |
| rate_converter_grid4/A/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `4.LOANS!J17` | 0.2682417946 | 0.08243216 | **D1** |
| rate_converter_grid5/A/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.2682417946 | 0.08243216 | **D1** |
| rate_converter_grid1/A/NOMINAL->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | 3.508195095e-05 | 0.07921050918 | **D2** |
| rate_converter_grid5/A/NOMINAL->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | 3.508195095e-05 | 0.07921050918 | **D2** |
| rate_converter_grid4/A/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `4.LOANS!J17` | 0 | 0.0234056908 | **D6** |
| rate_converter_grid5/A/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.0234056908 | **D7** |
| rate_converter_grid4/A/SIMPLE->NOMINAL | converted_rate | `4.LOANS!J17` | 0 | 0.2808682896 | **D6** |
| rate_converter_grid5/A/SIMPLE->NOMINAL | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.2808682896 | **D7** |
| rate_converter_grid4/A/SIMPLE->SIMPLE | converted_rate | `4.LOANS!J17` | 0 | 0.02666666667 | **D6** |
| rate_converter_grid5/A/SIMPLE->SIMPLE | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.02666666667 | **D7** |
| rate_converter_grid1/A/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `1. RATE CONVERTER!O17` | 0.006688938354 | 0.08328706767 | **D3** |
| rate_converter_grid2/A/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.006688938354 | 0.08328706767 | **D3** |
| rate_converter_grid3/A/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `3. ANNUITIES!L17` | 0.006688938354 | 0.08328706767 | **D3** |
| rate_converter_grid4/A/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `4.LOANS!J17` | 0.006688938354 | 0.08328706767 | **D3** |
| rate_converter_grid5/A/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.006688938354 | 0.08328706767 | **D3** |
| rate_converter_grid1/A/CONTINUOUS->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | `ERROR` | 0.08 | **D4** |
| rate_converter_grid2/A/CONTINUOUS->CONTINUOUS | converted_rate | `2. SINGLE INVESTMENTS!E19` | `ERROR` | 0.08 | **D4** |
| rate_converter_grid3/A/CONTINUOUS->CONTINUOUS | converted_rate | `3. ANNUITIES!L17` | `ERROR` | 0.08 | **D4** |
| rate_converter_grid4/A/CONTINUOUS->CONTINUOUS | converted_rate | `4.LOANS!J17` | `ERROR` | 0.08 | **D4** |
| rate_converter_grid5/A/CONTINUOUS->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | `ERROR` | 0.08 | **D4** |
| rate_converter_grid1/B/NOMINAL->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | 1.819647869e-16 | 0.04989612178 | **D2** |
| rate_converter_grid5/B/NOMINAL->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | 1.819647869e-16 | 0.04989612178 | **D2** |
| rate_converter_grid4/B/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `4.LOANS!J17` | 0 | 0.2649110641 | **D6** |
| rate_converter_grid5/B/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.2649110641 | **D7** |
| rate_converter_grid4/B/SIMPLE->NOMINAL | converted_rate | `4.LOANS!J17` | 0 | 0.5298221281 | **D6** |
| rate_converter_grid5/B/SIMPLE->NOMINAL | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.5298221281 | **D7** |
| rate_converter_grid4/B/SIMPLE->SIMPLE | converted_rate | `4.LOANS!J17` | 0 | 0.3 | **D6** |
| rate_converter_grid5/B/SIMPLE->SIMPLE | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.3 | **D7** |
| rate_converter_grid1/B/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `1. RATE CONVERTER!O17` | 0.02531512052 | 0.05127109638 | **D3** |
| rate_converter_grid2/B/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.02531512052 | 0.05127109638 | **D3** |
| rate_converter_grid3/B/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `3. ANNUITIES!L17` | 0.02531512052 | 0.05127109638 | **D3** |
| rate_converter_grid4/B/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `4.LOANS!J17` | 0.02531512052 | 0.05127109638 | **D3** |
| rate_converter_grid5/B/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.02531512052 | 0.05127109638 | **D3** |
| rate_converter_grid1/B/CONTINUOUS->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | `ERROR` | 0.05 | **D4** |
| rate_converter_grid2/B/CONTINUOUS->CONTINUOUS | converted_rate | `2. SINGLE INVESTMENTS!E19` | `ERROR` | 0.05 | **D4** |
| rate_converter_grid3/B/CONTINUOUS->CONTINUOUS | converted_rate | `3. ANNUITIES!L17` | `ERROR` | 0.05 | **D4** |
| rate_converter_grid4/B/CONTINUOUS->CONTINUOUS | converted_rate | `4.LOANS!J17` | `ERROR` | 0.05 | **D4** |
| rate_converter_grid5/B/CONTINUOUS->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | `ERROR` | 0.05 | **D4** |
| rate_converter_grid1/C/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `1. RATE CONVERTER!O17` | 1.012196472 | 0.06 | **D1** |
| rate_converter_grid2/C/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 1.012196472 | 0.06 | **D1** |
| rate_converter_grid3/C/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `3. ANNUITIES!L17` | 1.012196472 | 0.06 | **D1** |
| rate_converter_grid4/C/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `4.LOANS!J17` | 1.012196472 | 0.06 | **D1** |
| rate_converter_grid5/C/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `5. INCREASING ANNUITIES!G41` | 1.012196472 | 0.06 | **D1** |
| rate_converter_grid4/C/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `4.LOANS!J17` | 0 | 0.06 | **D6** |
| rate_converter_grid5/C/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.06 | **D7** |
| rate_converter_grid4/C/SIMPLE->NOMINAL | converted_rate | `4.LOANS!J17` | 0 | 0.06 | **D6** |
| rate_converter_grid5/C/SIMPLE->NOMINAL | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.06 | **D7** |
| rate_converter_grid4/C/SIMPLE->SIMPLE | converted_rate | `4.LOANS!J17` | 0 | 0.06 | **D6** |
| rate_converter_grid5/C/SIMPLE->SIMPLE | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.06 | **D7** |
| rate_converter_grid1/C/CONTINUOUS->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | `ERROR` | 0.06 | **D4** |
| rate_converter_grid2/C/CONTINUOUS->CONTINUOUS | converted_rate | `2. SINGLE INVESTMENTS!E19` | `ERROR` | 0.06 | **D4** |
| rate_converter_grid3/C/CONTINUOUS->CONTINUOUS | converted_rate | `3. ANNUITIES!L17` | `ERROR` | 0.06 | **D4** |
| rate_converter_grid4/C/CONTINUOUS->CONTINUOUS | converted_rate | `4.LOANS!J17` | `ERROR` | 0.06 | **D4** |
| rate_converter_grid5/C/CONTINUOUS->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | `ERROR` | 0.06 | **D4** |
| rate_converter_grid1/D/EFFECTIVE_ANNUAL->SIMPLE | converted_rate | `1. RATE CONVERTER!O17` | 0.005833333333 | 0.01875358333 | **D5** |
| rate_converter_grid2/D/EFFECTIVE_ANNUAL->SIMPLE | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.005833333333 | 0.01875358333 | **D5** |
| rate_converter_grid3/D/EFFECTIVE_ANNUAL->SIMPLE | converted_rate | `3. ANNUITIES!L17` | 0.005833333333 | 0.01875358333 | **D5** |
| rate_converter_grid4/D/EFFECTIVE_ANNUAL->SIMPLE | converted_rate | `4.LOANS!J17` | 0.005833333333 | 0.01875358333 | **D5** |
| rate_converter_grid5/D/EFFECTIVE_ANNUAL->SIMPLE | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.005833333333 | 0.01875358333 | **D5** |
| rate_converter_grid1/D/EFFECTIVE_ANNUAL->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | 9.592678943e-08 | 0.06765864847 | **D2** |
| rate_converter_grid2/D/EFFECTIVE_ANNUAL->CONTINUOUS | converted_rate | `2. SINGLE INVESTMENTS!E19` | 9.592678943e-08 | 0.06765864847 | **D2** |
| rate_converter_grid3/D/EFFECTIVE_ANNUAL->CONTINUOUS | converted_rate | `3. ANNUITIES!L17` | 9.592678943e-08 | 0.06765864847 | **D2** |
| rate_converter_grid4/D/EFFECTIVE_ANNUAL->CONTINUOUS | converted_rate | `4.LOANS!J17` | 9.592678943e-08 | 0.06765864847 | **D2** |
| rate_converter_grid5/D/EFFECTIVE_ANNUAL->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | 9.592678943e-08 | 0.06765864847 | **D2** |
| rate_converter_grid1/D/EFFECTIVE_PERIODIC->SIMPLE | converted_rate | `1. RATE CONVERTER!O17` | 0.036225 | 0.04172752932 | **D5** |
| rate_converter_grid2/D/EFFECTIVE_PERIODIC->SIMPLE | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.036225 | 0.04172752932 | **D5** |
| rate_converter_grid3/D/EFFECTIVE_PERIODIC->SIMPLE | converted_rate | `3. ANNUITIES!L17` | 0.036225 | 0.04172752932 | **D5** |
| rate_converter_grid4/D/EFFECTIVE_PERIODIC->SIMPLE | converted_rate | `4.LOANS!J17` | 0.036225 | 0.04172752932 | **D5** |
| rate_converter_grid5/D/EFFECTIVE_PERIODIC->SIMPLE | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.036225 | 0.04172752932 | **D5** |
| rate_converter_grid1/D/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `1. RATE CONVERTER!O17` | 0.5110686573 | 0.071225 | **D1** |
| rate_converter_grid2/D/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.5110686573 | 0.071225 | **D1** |
| rate_converter_grid3/D/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `3. ANNUITIES!L17` | 0.5110686573 | 0.071225 | **D1** |
| rate_converter_grid4/D/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `4.LOANS!J17` | 0.5110686573 | 0.071225 | **D1** |
| rate_converter_grid5/D/NOMINAL->EFFECTIVE_ANNUAL | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.5110686573 | 0.071225 | **D1** |
| rate_converter_grid1/D/NOMINAL->SIMPLE | converted_rate | `1. RATE CONVERTER!O17` | 0.01780625 | 0.01910461053 | **D5** |
| rate_converter_grid2/D/NOMINAL->SIMPLE | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.01780625 | 0.01910461053 | **D5** |
| rate_converter_grid3/D/NOMINAL->SIMPLE | converted_rate | `3. ANNUITIES!L17` | 0.01780625 | 0.01910461053 | **D5** |
| rate_converter_grid4/D/NOMINAL->SIMPLE | converted_rate | `4.LOANS!J17` | 0.01780625 | 0.01910461053 | **D5** |
| rate_converter_grid5/D/NOMINAL->SIMPLE | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.01780625 | 0.01910461053 | **D5** |
| rate_converter_grid1/D/NOMINAL->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | 9.20194893e-15 | 0.06880285343 | **D2** |
| rate_converter_grid2/D/NOMINAL->CONTINUOUS | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.4128171206 | 0.06880285343 | **D5** |
| rate_converter_grid3/D/NOMINAL->CONTINUOUS | converted_rate | `3. ANNUITIES!L17` | 0.4128171206 | 0.06880285343 | **D5** |
| rate_converter_grid4/D/NOMINAL->CONTINUOUS | converted_rate | `4.LOANS!J17` | 0.4128171206 | 0.06880285343 | **D5** |
| rate_converter_grid5/D/NOMINAL->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | 9.20194893e-15 | 0.06880285343 | **D2** |
| rate_converter_grid1/D/SIMPLE->EFFECTIVE_ANNUAL | converted_rate | `1. RATE CONVERTER!O17` | 0.14 | 0.1069711537 | **D5** |
| rate_converter_grid2/D/SIMPLE->EFFECTIVE_ANNUAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.14 | 0.1069711537 | **D5** |
| rate_converter_grid3/D/SIMPLE->EFFECTIVE_ANNUAL | converted_rate | `3. ANNUITIES!L17` | 0.14 | 0.1069711537 | **D5** |
| rate_converter_grid4/D/SIMPLE->EFFECTIVE_ANNUAL | converted_rate | `4.LOANS!J17` | 0.14 | 0.1069711537 | **D5** |
| rate_converter_grid5/D/SIMPLE->EFFECTIVE_ANNUAL | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.14 | 0.1069711537 | **D5** |
| rate_converter_grid1/D/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `1. RATE CONVERTER!O17` | 0.03329948476 | 0.02573240493 | **D5** |
| rate_converter_grid2/D/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.03329948476 | 0.02573240493 | **D5** |
| rate_converter_grid3/D/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `3. ANNUITIES!L17` | 0.03329948476 | 0.02573240493 | **D5** |
| rate_converter_grid4/D/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `4.LOANS!J17` | 0 | 0.02573240493 | **D6** |
| rate_converter_grid5/D/SIMPLE->EFFECTIVE_PERIODIC | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.02573240493 | **D7** |
| rate_converter_grid1/D/SIMPLE->NOMINAL | converted_rate | `1. RATE CONVERTER!O17` | 0.133197939 | 0.1029296197 | **D5** |
| rate_converter_grid2/D/SIMPLE->NOMINAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.133197939 | 0.1029296197 | **D5** |
| rate_converter_grid3/D/SIMPLE->NOMINAL | converted_rate | `3. ANNUITIES!L17` | 0.133197939 | 0.1029296197 | **D5** |
| rate_converter_grid4/D/SIMPLE->NOMINAL | converted_rate | `4.LOANS!J17` | 0 | 0.1029296197 | **D6** |
| rate_converter_grid5/D/SIMPLE->NOMINAL | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.1029296197 | **D7** |
| rate_converter_grid1/D/SIMPLE->SIMPLE | converted_rate | `1. RATE CONVERTER!O17` | 0.035 | 0.02970549972 | **D5** |
| rate_converter_grid2/D/SIMPLE->SIMPLE | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.035 | 0.02970549972 | **D5** |
| rate_converter_grid3/D/SIMPLE->SIMPLE | converted_rate | `3. ANNUITIES!L17` | 0.035 | 0.02970549972 | **D5** |
| rate_converter_grid4/D/SIMPLE->SIMPLE | converted_rate | `4.LOANS!J17` | 0 | 0.02970549972 | **D6** |
| rate_converter_grid5/D/SIMPLE->SIMPLE | converted_rate | `5. INCREASING ANNUITIES!G41` | `#NAME?` | 0.02970549972 | **D7** |
| rate_converter_grid1/D/SIMPLE->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | 0.6097655716 | 0.1016275953 | **D5** |
| rate_converter_grid2/D/SIMPLE->CONTINUOUS | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.6097655716 | 0.1016275953 | **D5** |
| rate_converter_grid3/D/SIMPLE->CONTINUOUS | converted_rate | `3. ANNUITIES!L17` | 0.6097655716 | 0.1016275953 | **D5** |
| rate_converter_grid4/D/SIMPLE->CONTINUOUS | converted_rate | `4.LOANS!J17` | 0.6097655716 | 0.1016275953 | **D5** |
| rate_converter_grid5/D/SIMPLE->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.6097655716 | 0.1016275953 | **D5** |
| rate_converter_grid1/D/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `1. RATE CONVERTER!O17` | 0.005850380353 | 0.07250818125 | **D3** |
| rate_converter_grid2/D/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.005850380353 | 0.07250818125 | **D3** |
| rate_converter_grid3/D/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `3. ANNUITIES!L17` | 0.005850380353 | 0.07250818125 | **D3** |
| rate_converter_grid4/D/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `4.LOANS!J17` | 0.005850380353 | 0.07250818125 | **D3** |
| rate_converter_grid5/D/CONTINUOUS->EFFECTIVE_ANNUAL | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.005850380353 | 0.07250818125 | **D3** |
| rate_converter_grid1/D/CONTINUOUS->EFFECTIVE_PERIODIC | converted_rate | `1. RATE CONVERTER!O17` | 0.005850380353 | 0.01765402215 | **D5** |
| rate_converter_grid2/D/CONTINUOUS->EFFECTIVE_PERIODIC | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.005850380353 | 0.01765402215 | **D5** |
| rate_converter_grid3/D/CONTINUOUS->EFFECTIVE_PERIODIC | converted_rate | `3. ANNUITIES!L17` | 0.005850380353 | 0.01765402215 | **D5** |
| rate_converter_grid4/D/CONTINUOUS->EFFECTIVE_PERIODIC | converted_rate | `4.LOANS!J17` | 0.005850380353 | 0.01765402215 | **D5** |
| rate_converter_grid5/D/CONTINUOUS->EFFECTIVE_PERIODIC | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.005850380353 | 0.01765402215 | **D5** |
| rate_converter_grid1/D/CONTINUOUS->NOMINAL | converted_rate | `1. RATE CONVERTER!O17` | 0.02340152141 | 0.0706160886 | **D5** |
| rate_converter_grid2/D/CONTINUOUS->NOMINAL | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.02340152141 | 0.0706160886 | **D5** |
| rate_converter_grid3/D/CONTINUOUS->NOMINAL | converted_rate | `3. ANNUITIES!L17` | 0.02340152141 | 0.0706160886 | **D5** |
| rate_converter_grid4/D/CONTINUOUS->NOMINAL | converted_rate | `4.LOANS!J17` | 0.02340152141 | 0.0706160886 | **D5** |
| rate_converter_grid5/D/CONTINUOUS->NOMINAL | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.02340152141 | 0.0706160886 | **D5** |
| rate_converter_grid1/D/CONTINUOUS->SIMPLE | converted_rate | `1. RATE CONVERTER!O17` | 0.006042348438 | 0.01947317166 | **D5** |
| rate_converter_grid2/D/CONTINUOUS->SIMPLE | converted_rate | `2. SINGLE INVESTMENTS!E19` | 0.006042348438 | 0.01947317166 | **D5** |
| rate_converter_grid3/D/CONTINUOUS->SIMPLE | converted_rate | `3. ANNUITIES!L17` | 0.006042348438 | 0.01947317166 | **D5** |
| rate_converter_grid4/D/CONTINUOUS->SIMPLE | converted_rate | `4.LOANS!J17` | 0.006042348438 | 0.01947317166 | **D5** |
| rate_converter_grid5/D/CONTINUOUS->SIMPLE | converted_rate | `5. INCREASING ANNUITIES!G41` | 0.006042348438 | 0.01947317166 | **D5** |
| rate_converter_grid1/D/CONTINUOUS->CONTINUOUS | converted_rate | `1. RATE CONVERTER!O17` | `ERROR` | 0.07 | **D4** |
| rate_converter_grid2/D/CONTINUOUS->CONTINUOUS | converted_rate | `2. SINGLE INVESTMENTS!E19` | `ERROR` | 0.07 | **D4** |
| rate_converter_grid3/D/CONTINUOUS->CONTINUOUS | converted_rate | `3. ANNUITIES!L17` | `ERROR` | 0.07 | **D4** |
| rate_converter_grid4/D/CONTINUOUS->CONTINUOUS | converted_rate | `4.LOANS!J17` | `ERROR` | 0.07 | **D4** |
| rate_converter_grid5/D/CONTINUOUS->CONTINUOUS | converted_rate | `5. INCREASING ANNUITIES!G41` | `ERROR` | 0.07 | **D4** |
| single_investment/S1/INTEREST_RATE/EFFECTIVE_ANNUAL | rate_out | `2. SINGLE INVESTMENTS!K18` | 2.623898318 | 0.1746189431 | **D9** |
| single_investment/S1/INTEREST_EARNED/EFFECTIVE_ANNUAL | answer | `2. SINGLE INVESTMENTS!K16` | 1,332.052026 | 3,187.48492 | **D8** |
| single_investment/S1/INTEREST_EARNED/EFFECTIVE_PERIODIC | answer | `2. SINGLE INVESTMENTS!K16` | 4,096,795.547 | 4,094,800.429 | **D8** |
| single_investment/S1/INTEREST_EARNED/NOMINAL | answer | `2. SINGLE INVESTMENTS!K16` | 1,701.302014 | 3,402.969882 | **D8** |
| single_investment/S1/INTEREST_EARNED/SIMPLE | answer | `2. SINGLE INVESTMENTS!K16` | 16,888.88889 | 16,000 | **D8** |
| single_investment/S1/INTEREST_EARNED/CONTINUOUS | answer | `2. SINGLE INVESTMENTS!K16` | 0 | 3,436.563657 | **D10** |
| single_investment/S2/INTEREST_RATE/EFFECTIVE_ANNUAL | rate_out | `2. SINGLE INVESTMENTS!K18` | 8.016874412 | 0.201124434 | **D9** |
| single_investment/S2/INTEREST_EARNED/EFFECTIVE_ANNUAL | answer | `2. SINGLE INVESTMENTS!K16` | -23,204.92443 | 2,081.616064 | **D8** |
| single_investment/S2/INTEREST_EARNED/EFFECTIVE_PERIODIC | answer | `2. SINGLE INVESTMENTS!K16` | 50,381.50244 | 45,620.61577 | **D8** |
| single_investment/S2/INTEREST_EARNED/NOMINAL | answer | `2. SINGLE INVESTMENTS!K16` | -23,144.0585 | 2,101.578531 | **D8** |
| single_investment/S2/INTEREST_EARNED/SIMPLE | answer | `2. SINGLE INVESTMENTS!K16` | 21,272.72727 | 24,000 | **D8** |
| single_investment/S2/INTEREST_EARNED/CONTINUOUS | answer | `2. SINGLE INVESTMENTS!K16` | 0 | 2,103.418362 | **D10** |
| single_investment/S3/INTEREST_EARNED/EFFECTIVE_ANNUAL | answer | `2. SINGLE INVESTMENTS!K16` | -1,178.691589 | 840 | **D8** |
| single_investment/S3/INTEREST_EARNED/EFFECTIVE_PERIODIC | answer | `2. SINGLE INVESTMENTS!K16` | -1,178.691589 | 840 | **D8** |
| single_investment/S3/INTEREST_EARNED/NOMINAL | answer | `2. SINGLE INVESTMENTS!K16` | -1,178.691589 | 840 | **D8** |
| single_investment/S3/INTEREST_EARNED/SIMPLE | answer | `2. SINGLE INVESTMENTS!K16` | -1,178.691589 | 840 | **D8** |
| single_investment/S3/INTEREST_EARNED/CONTINUOUS | answer | `2. SINGLE INVESTMENTS!K16` | 0 | 870.0981751 | **D10** |
| annuities/A2 | arrears.future_value | `3. ANNUITIES!P24` | 329,938.6895 | 230,038.6895 | **D11** |
| annuities/A2 | arrears.rate_from_fv | `3. ANNUITIES!P30` | 0.01649693447 | 0.007984103181 | **D13** |
| annuities/A2 | arrears.rate_from_pv | `3. ANNUITIES!P31` | 0.01394010441 | 0.01750847078 | **D13** |
| annuities/A2 | advance.years_from_fv | `3. ANNUITIES!R26` | 9.25644959 | 9.145338683 | **D12** |
| annuities/A2 | advance.years_from_pv | `3. ANNUITIES!R27` | 5.889230609 | 5.722547439 | **D12** |
| annuities/A2 | advance.rate_from_fv | `3. ANNUITIES!R30` | 0.01161695382 | 0.007869326585 | **D13** |
| annuities/A2 | advance.rate_from_pv | `3. ANNUITIES!R31` | 0.01407950545 | 0.01795201594 | **D13** |
| annuities/A3 | arrears.future_value | `3. ANNUITIES!P24` | 118,780.0739 | 35,480.0739 | **D11** |
| annuities/A3 | arrears.rate_from_fv | `3. ANNUITIES!P30` | 0.08908505543 | 0.05089675268 | **D13** |
| annuities/A3 | arrears.rate_from_pv | `3. ANNUITIES!P31` | 0.02986201198 | 0.02922854077 | **D13** |
| annuities/A3 | advance.years_from_fv | `3. ANNUITIES!R26` | 3.397674787 | 3.23550702 | **D12** |
| annuities/A3 | advance.years_from_pv | `3. ANNUITIES!R27` | 3.126103116 | 2.911734585 | **D12** |
| annuities/A3 | advance.rate_from_fv | `3. ANNUITIES!R30` | 0.02740835709 | 0.04351932184 | **D13** |
| annuities/A3 | advance.rate_from_pv | `3. ANNUITIES!R31` | 0.03075787234 | 0.03503153036 | **D13** |
| annuities/A4 | arrears.future_value | `3. ANNUITIES!P24` | 529,432.7161 | 369,632.7161 | **D11** |
| annuities/A4 | arrears.rate_from_fv | `3. ANNUITIES!P30` | 0.006617908952 | 0.005550781904 | **D13** |
| annuities/A4 | arrears.rate_from_pv | `3. ANNUITIES!P31` | 0.005583230867 | 0.006173646637 | **D13** |
| annuities/A4 | advance.years_from_fv | `3. ANNUITIES!R26` | 20.99110407 | 20.87205651 | **D12** |
| annuities/A4 | advance.years_from_pv | `3. ANNUITIES!R27` | 16.52780735 | 16.25001626 | **D12** |
| annuities/A4 | advance.rate_from_fv | `3. ANNUITIES!R30` | 0.004643510996 | 0.005512719804 | **D13** |
| annuities/A4 | advance.rate_from_pv | `3. ANNUITIES!R31` | 0.005611147022 | 0.0062418251 | **D13** |
| annuities/A5 | arrears.future_value | `3. ANNUITIES!P24` | 396,508.6393 | 271,521.1393 | **D11** |
| annuities/A5 | arrears.rate_from_fv | `3. ANNUITIES!P30` | 0.1057356371 | 0.09273677281 | **D13** |
| annuities/A5 | arrears.rate_from_pv | `3. ANNUITIES!P31` | 0.08559478688 | 0.0912829653 | **D13** |
| annuities/A5 | advance.years_from_fv | `3. ANNUITIES!R26` | 16.61501887 | 15.20342287 | **D12** |
| annuities/A5 | advance.years_from_pv | `3. ANNUITIES!R27` | 15.26826357 | 11.6674824 | **D12** |
| annuities/A5 | advance.rate_from_fv | `3. ANNUITIES!R30` | 0.07819808811 | 0.0826132028 | **D13** |
| annuities/A5 | advance.rate_from_pv | `3. ANNUITIES!R31` | 0.09244236983 | 0.1095091731 | **D13** |
| annuities/A6 | arrears.future_value | `3. ANNUITIES!P24` | 16,355.15394 | 11,405.15394 | **D11** |
| annuities/A6 | arrears.rate_from_fv | `3. ANNUITIES!P30` | 0.04672901126 | 0.005106655058 | **D13** |
| annuities/A6 | arrears.rate_from_pv | `3. ANNUITIES!P31` | 0.006952177335 | -0.01544514669 | **D13** |
| annuities/A6 | advance.years_from_fv | `3. ANNUITIES!R26` | 3.732955312 | 3.635733532 | **D12** |
| annuities/A6 | advance.rate_from_fv | `3. ANNUITIES!R30` | 0.0332378772 | 0.004946685743 | **D13** |
| annuities/A6 | advance.rate_from_pv | `3. ANNUITIES!R31` | 0.007091220882 | -0.01589358045 | **D13** |
| loans/L2 | arrears.balance_at_T_plus_1 | `4.LOANS!P37` | 37,024.86708 | -255,832.7212 | **D16** |
| loans/L2 | advance.interest_next_payment | `4.LOANS!U30` | -722.5422073 | -718.9474699 | **D15** |
| loans/L2 | advance.capital_next_payment | `4.LOANS!U31` | 9,222.542207 | 9,218.94747 | **D15** |
| loans/L3 | arrears.balance_at_T_plus_1 | `4.LOANS!P37` | 78,829.33127 | 950,626.3194 | **D16** |
| loans/L3 | advance.interest_next_payment | `4.LOANS!U30` | 8,118.526568 | 8,050.100712 | **D15** |
| loans/L3 | advance.capital_next_payment | `4.LOANS!U31` | 881.4734316 | 949.8992877 | **D15** |
| loans/L3 | advance.payments_needed | `4.LOANS!U32` | 342 | 326 | **D14** |
| loans/L3 | advance.last_payment | `4.LOANS!U33` | -147,979.3149 | 6,008.876465 | **D14** |
| loans/L4 | arrears.balance_at_T_plus_1 | `4.LOANS!P37` | -1,434.27409 | -9,886.854818 | **D16** |
| loans/L4 | advance.interest_next_payment | `4.LOANS!U30` | 801.2005527 | 781.6590758 | **D15** |
| loans/L4 | advance.capital_next_payment | `4.LOANS!U31` | 11,198.79945 | 11,218.34092 | **D15** |
| loans/L4 | advance.payments_needed | `4.LOANS!U32` | 16 | 15 | **D14** |
| loans/L4 | advance.last_payment | `4.LOANS!U33` | -3,317.972942 | 8,762.953227 | **D14** |
| loans/L5 | arrears.balance_at_T_plus_1 | `4.LOANS!P37` | 424,090.9552 | 405,128.29 | **D16** |
| loans/L5 | advance.interest_next_payment | `4.LOANS!U30` | 37,655.024 | 34,231.84 | **D15** |
| loans/L5 | advance.capital_next_payment | `4.LOANS!U31` | 22,344.976 | 25,768.16 | **D15** |
| loans/L5 | advance.payments_needed | `4.LOANS!U32` | 19 | 15 | **D14** |
| loans/L5 | advance.last_payment | `4.LOANS!U33` | -229,586.7702 | 52,400.26627 | **D14** |
| loans/L6 | arrears.balance_at_T_plus_1 | `4.LOANS!P37` | 709.3176978 | 28,307.74597 | **D16** |
| loans/L6 | advance.interest_next_payment | `4.LOANS!U30` | 470.9237288 | 466.2611176 | **D15** |
| loans/L6 | advance.capital_next_payment | `4.LOANS!U31` | 1,529.076271 | 1,533.738882 | **D15** |
| loans/L6 | advance.payments_needed | `4.LOANS!U32` | 52 | 51 | **D14** |
| loans/L6 | advance.last_payment | `4.LOANS!U33` | -651.5330876 | 1,354.917735 | **D14** |
| loans/L7 | arrears.balance_at_T_plus_1 | `4.LOANS!P37` | 569.6966568 | 98,607.7 | **D16** |
| loans/L7 | advance.interest_next_payment | `4.LOANS!U30` | 9,559.77 | 8,690.7 | **D15** |
| loans/L7 | advance.capital_next_payment | `4.LOANS!U31` | 740.23 | 1,609.3 | **D15** |
| loans/L7 | advance.payments_needed | `4.LOANS!U32` | 38 | 23 | **D14** |
| loans/L7 | advance.last_payment | `4.LOANS!U33` | -338,952.5162 | 5,034.343316 | **D14** |

</details>
