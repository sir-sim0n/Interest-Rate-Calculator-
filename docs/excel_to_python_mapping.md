# Excel → Python mapping

This document maps every input and output cell of `INTEREST-RATE-CALCULATOR-48581275.xlsx` to the Python code that replaces it. The machine-readable version of the same mapping is `validation/excel_spec.py`, which the parity tests use.

Notation: i is the rate per period, n the number of payments or periods, p periods per year, X the installment, L the loan amount. Defect IDs (D1–D18) refer to `docs/validation_report.md`.

---

## How the translation was done

| Excel pattern | Python replacement | Why |
|---|---|---|
| A 5 × 5 grid of conversion formulas, copied five times (125 formulas), plus five 24-branch nested `IF` lookups | `rates.to_effective_annual()` + `rates.from_effective_annual()`: 5 + 5 formulas, combined by `rates.convert_rate()` | Every conversion goes through the effective annual rate (hub and spoke), so the 25 pairs need only 10 formulas and one copy. |
| Helper cells on `BACKROOM1` (e.g. `L24:P28`, `U9:AD24`, `AM38:AN44`) | Small named functions (`growth_factor`, `accumulation_factor`, `balance`, `year_totals` ...) | A helper cell's meaning becomes the function's name and docstring. |
| Nested `IF(AND(K13=..., K14=...), ...)` choosing a result | `Outcome` / `RateType` enums plus one `solve()` dispatch | Replaces string matching on labels like `'PRESENT VALUE '` (with a trailing space). |
| Dropdown text values (`"continous"`, `"SIMPLE "`) | `RateType`, `Timing`, `Outcome` enums in `calculator/common.py` | Typos and stray spaces can't cause silent mismatches. |
| "Use interest from converter / with no conversion" dropdown with a copied value | `ui.components.rate_input()`: enter the rate, or convert a quoted rate. Always live | Fixes stale values (D17). |
| Arrears and advance in two columns of near-identical formulas | One function with a `timing` argument; advance = arrears × (1+i) where applicable | One formula to maintain instead of two. |
| `#NUM!`, `#DIV/0!`, `"ERROR"`, `"-"` | `CalculationError` with a plain-English reason; outputs that don't apply are not shown | The user learns why, not just that it failed. |
| `RAND()` recalculated on every edit | `random.Random(seed)`, drawn only when the user asks | Reproducible results and testable code. |
| `INDIRECT()` named ranges for dependent dropdowns, prices copied into lists | `calculator/data/companies.csv` + `broker.MarketData` lookups | Fixes three companies Excel could not price (D18); the data is editable without touching code. |
| `(end − start)/365` from `DATE(y, m, d)` cells | `dates.years_between(start, end)` | Same Actual/365 convention, with date pickers instead of three number cells. |

Mathematical equivalence was kept wherever the workbook is correct. Where the Python formula is written differently (e.g. `math.log(x) / math.log(1 + i)` for Excel's `LOG(x, 1+i)`), the results agree to about 1e-13 relative difference.

---

## 1. Rate converter: `1. RATE CONVERTER` (+ embedded grids 2–5)

| Excel | Meaning | Python |
|---|---|---|
| `P11` / `P12` / `P13` / `P14` | quoted rate, its periods per year, its type, its term in years | `convert_rate(rate, from_type, …, from_periods, …, from_years)` |
| `R12` / `R13` / `R14` | target periods per year, type, years | `to_periods`, `to_type`, `to_years` |
| `BACKROOM1!A1:F13` | the 5 × 5 grid of conversion formulas | `to_effective_annual()` then `from_effective_annual()` |
| `O17` | converted rate (24-branch nested `IF` over the grid) | `rates.convert_rate(...)` |

The same converter is embedded on the other sheets:

| Sheet | Inputs | Output | Python |
|---|---|---|---|
| 2. SINGLE INVESTMENTS | `C14:C17`, `E15:E17` | `E19` | `rate_input(..., to_type=<interest type>, to_periods=p)` |
| 3. ANNUITIES | `J13:J16`, `L15:L16`, `Q10` | `L17` | `rate_input(..., to_type=EFFECTIVE_PERIODIC, to_periods=p)` |
| 4.LOANS | `H13:H16`, `J15:J16`, `R15` | `J17` | same as annuities |
| 5. INCREASING ANNUITIES | `E36:E39`, `G37:G39` | `G41` → `J37` | same, with p = `J39` |

Formulas (i = effective annual rate):

| Type | to effective annual | from effective annual |
|---|---|---|
| Effective annual i | i | i |
| Effective periodic j | (1 + j)^p − 1 | (1 + i)^(1/p) − 1 |
| Nominal i(p) | (1 + i(p)/p)^p − 1 | p · ((1 + i)^(1/p) − 1) |
| Continuous δ | e^δ − 1 | ln(1 + i) |
| Simple r (per period) over n years | (1 + r·p·n)^(1/n) − 1 | ((1 + i)^n − 1) / (p·n) |

In the embedded converters, the target type and frequency are fixed to what that calculator needs (the effective rate per payment period for annuities and loans; the selected interest type and p for single investments). In Excel these could be set to values that don't fit the calculation.

## 2. Single investments: `2. SINGLE INVESTMENTS`

| Excel | Meaning | Python (`calculator/single_investment.py`) |
|---|---|---|
| `C5:C8`, `E5:E8`, `E9` | start/end date, years between | `dates.years_between()` |
| `K6`, `K7`, `K8`, `K9`, `K10` | FV, PV, rate, years, periods per year | `fv`, `pv`, `rate`, `years`, `periods_per_year` |
| `K13` | outcome (`'FUTURE VALUE'`, `'PRESENT VALUE '`, `'YEARS'`, `'INTEREST'`, `'INTEREST EARNED'`) | `Outcome` enum |
| `K14` | interest type (`'SIMPLE '`, `'EFFECTIVE PERIODIC'`, `'EFFECTIVE ANNUAL'`, `'NOMINAL '`, `'CONTINOUS'`) | `RateType` enum |
| `BACKROOM1!L24:L28` | FV per interest type, e.g. `L24 = PV*(1 + r*p*n)`, `L28 = PV*EXP(1)^(δ*n)` | `growth_factor(rate, type, years, p)` × PV → `future_value()` |
| `BACKROOM1!M24:M28` | PV per type | `present_value()` |
| `BACKROOM1!N24:N28` | years per type | `solve_years()` |
| `BACKROOM1!O24:O28` | rate per type | `solve_rate()` (D9 fixed) |
| `BACKROOM1!P24:P28` | interest earned per type | `interest_earned()` = FV − PV (D8, D10 fixed) |
| `K16` / `K17` / `K18` | the selected result (FV/PV/earned, years, rate), otherwise `"-"` | `solve(outcome, type, pv=…, fv=…, rate=…, years=…, periods_per_year=…)` |
| Chart 1 | FV by interest type | `compare_interest_types()` (table on the page) |
| — | new: value at every year end | `growth_table()` |

## 3. Annuities: `3. ANNUITIES`

Inputs: `Q7` installment → `installment`, `Q8` rate → `rate`, `Q9` years → `years`, `Q10` payments per year → `periods_per_year`, `Q11` PV → `pv`, `Q12` FV → `fv`. n = Q9 × Q10.

| Output | Arrears | Advance | Excel formula (arrears) | Python (`calculator/annuities.py`) |
|---|---|---|---|---|
| Future value | `P24` | `R24` | `(Q7*(1+Q8)^(Q9*Q10)-1)/Q8` (D11) | `future_value(X, i, n, timing)` = X·s_n |
| Present value | `P25` | `R25` | `(Q7*(1-(1+Q8)^(-Q9*Q10)))/Q8` | `present_value()` = X·a_n |
| Years given FV | `P26` | `R26` | `LOG(BACKROOM1!V28, 1+Q8)/Q10` | `term_from_fv() / p` (D12 fixed in advance) |
| Years given PV | `P27` | `R27` | `LOG(BACKROOM1!U25, 1/(1+Q8))/Q10` | `term_from_pv() / p` |
| Installment given FV | `P28` | `R28` | `(Q12*Q8)/((1+Q8)^(Q9*Q10)-1)` | `installment_from_fv()` |
| Installment given PV | `P29` | `R29` | `(Q11*Q8)/(1-(1+Q8)^(BACKROOM1!V25))` | `installment_from_pv()` |
| Rate given FV | `P30` | `R30` | `(Q7*(1+Q8)^(Q9*Q10)-1)/Q12` (D13) | `rate_from_fv()` (bisection) |
| Rate given PV | `P31` | `R31` | value ratio (D13) | `rate_from_pv()` (bisection) |

`annuity_summary(...)` returns all eight outputs for one timing as an `AnnuityResults` dataclass, with any `CalculationError` messages in `.errors`.

## 4. Loans: `4.LOANS`

Inputs: `R11` loan → `principal`, `R12` installment → `installment_`, `R13` years (from dates `H4:J7`) → `years`, `R14` rate → `rate`, `R15` payments per year → `periods_per_year`, `R16` year T → `year_T`. Derived: n = `BACKROOM1!AM38` = `R13*R15`, t = `R18` = `R16*R15`.

| Output | Arrears | Advance | Excel formula (arrears) | Python (`calculator/loans.py`) |
|---|---|---|---|---|
| Installment that repays L in n | `P27` | `U27` | `(R11*R14)/(1-(1+R14)^(-R15*R13))` | `installment(L, i, n, timing)` |
| Loan the installment repays | `P28` | `U28` | `R12*(1-(1+R14)^(-AM38))/R14` | `loan_amount(X, i, n, timing)` |
| Balance at T | `P29` | `U29` | `R11*(1+R14)^R18 - R12*((1+R14)^R18-1)/R14` | `balance(L, X, i, t, timing)` |
| Interest in next payment | `P30` | `U30` | `(AQ19-R12)*(1+R14)^R18+R12` (= i·B_t); advance `U29*R14` (D15) | `interest_in_payment(L, X, i, t, timing)` |
| Capital in next payment | `P31` | `U31` | `R12-P30` | `capital_in_payment()` |
| Payments needed | `P32` | `U32` | `ROUNDUP(-LN(1-(R11*R14)/R12)/LN(1+R14),0)`, same in advance (D14) | `payments_needed()` |
| Last payment | `P33` | `U33` | balance after N − 1 payments × (1+i) | `last_payment()` |
| Capital in year T | `P34` | (blank) | `AM44-AN44` | `year_totals(...).capital` (advance is new) |
| Interest in year T | `P35` | (blank) | cumulative-interest difference | `year_totals(...).interest` |
| Total interest | `P36` | `U36` | `(R13*R15)*R12-R11` | `total_interest(L, X, n)` |
| Balance at T + 1 | `P37` | — | `R13*P33-R12` (D16) | `balance(L, X, i, t + p, timing)` |
| — | — | — | new | `amortisation_schedule()`: a period-by-period table, also used by the tests as an independent check |

`loan_summary(...)` returns everything as a `LoanResults` dataclass, plus `.warnings`, e.g. when the installment doesn't cover the interest, or the term gives a fractional number of payments.

## 5. Increasing annuities: `5. INCREASING ANNUITIES`

Part 1 inputs: `I8` i, `I9` X, `I10` N, `I11` P, `I12` k, `I13` m, `I14` j, `I15` PV, `I16` FV.

| Output | Every k-th payment increasing (arrears / advance) | Every payment increasing (arrears / advance) | Python (`calculator/increasing_annuities.py`) |
|---|---|---|---|
| Installment given FV | `E23` / `G23` | `K23` / `M23` | `stepped_installment_from_fv()`, `geometric_installment_from_fv()` |
| Installment given PV | `E24` / `G24` | `K24` / `M24` | `…_installment_from_pv()` |
| Future value | `E25` / `G25` | `K25` / `M25` | `stepped_future_value()`, `geometric_future_value()` |
| Present value | `E26` / `G26` | `K26` / `M26` | `…_present_value()` |

Excel formulas: `K25 = I9*((1+I8)^(I11*I10)-(1+I14)^(I11*I10))/(I8-I14)` → `geometric_future_value`. `E25 = BACKROOM1!AX7*(AY7/AZ7)`, i.e. X·s_k · ((1+i)^(km) − (1+j)^m) / ((1+i)^k − (1+j)) → `stepped_fv_factor`. When i = j (or (1+i)^k = 1+j), Excel divides by zero; Python uses the mathematical limit.

Part 2 (retirement plan), all through `plan_retirement(RetirementInputs) -> RetirementResult`:

| Excel | Meaning | Python field |
|---|---|---|
| `J36` | lump sum today | `lump_sum` |
| `J37` (= `G41` converter) | rate per period | `rate` |
| `J38` | inflation per year | `inflation` |
| `J39`, `J40` | lump-sum compounding p, years | `lump_sum_periods_per_year`, `lump_sum_years` |
| `J41`, `J42` | contributions k per year, m years | `contribution_k`, `contribution_m` |
| `K36`, `K40` | first withdrawal in today's money, years to inflate | `first_withdrawal_today`, `years_to_inflate` |
| `K41`, `K42` | withdrawals k per year, m years | `withdrawal_k`, `withdrawal_m` |
| `N36` = `BACKROOM1!BM12` | first withdrawal inflated, W₀(1+j)^years | `first_withdrawal` |
| `N37` = `BK18` | FV of withdrawals | `withdrawals_fv` |
| `N38` = `BK19` | value of withdrawals at retirement | `withdrawals_pv` |
| `N39` = `BM5` | lump sum at retirement, C(1+i)^(p·n) | `lump_sum_fv` |
| `N40` = `BK20` = `(BK19-BM5)/BK17` | first contribution | `first_contribution` |

## 6. The Easy Broker: `TEB` + `BACKROOM2_TEB`

| Excel | Meaning | Python (`calculator/broker.py`) |
|---|---|---|
| `BACKROOM2_TEB` company lists and prices | companies per exchange and country | `calculator/data/companies.csv` → `MarketData` |
| `BACKROOM2_TEB` return bands, `C28:C35 = RAND()*width+low` | simulated annual return per country | `country_returns.csv` → `sample_return(band, rng)`, `sample_all_returns()` |
| `B23` (Microsoft 365 currency data type) | USD/ZAR | `DEFAULT_USD_ZAR` = 17.9954 (22 Aug 2024), `fetch_live_usd_zar()` |
| `G5`, `H5`, `I5` (`INDIRECT` lookup), `I7` | exchange, company, price, shares | `companies_on_exchange()`, `company().price_usd` |
| `I8 = I7*I5`, `I9 = I8*B23` | cost in USD, ZAR | `purchase_cost_usd()`, `to_zar()` |
| `G15`, `H15`, `I15`, `I17`, `I18`, `I19` | the same, by country | `companies_in_country()`, same functions |
| `I25`, `I26 = I19*(1+C28…C35)^I25` | years, projected value | `projected_value(cost_zar, annual_return, years)` |
| Chart 2 | returns by country | bar chart on the page |

`tools/export_market_data.py` regenerates the two CSV files from the workbook, and `tests/test_broker_and_dates.py` checks them against it.
