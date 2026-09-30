# Interest Rate Calculator: Excel → Python

## Phase 1–2 Analysis and Proposed Architecture (for approval before coding)

Source files inspected:

| File | What it is | Role in this conversion |
|---|---|---|
| `INTEREST-RATE-CALCULATOR-48581275.xlsx` | The working calculator (9 sheets, 346 formulas) | Source of truth for behaviour and calculations |
| `2024_Interest_Calculator_Information-1.pdf` | BWIA 121 project brief (3 pages) | Intended purpose and required functionality |
| `INTEREST-RATE-CALCULATOR.pptx` | 10-slide presentation of the calculator | Intended use of each sheet |

How the workbook was inspected: every cell, formula, cached value, number format, merged range, defined name, table, chart, drawing/hyperlink and data-validation rule (including the Excel 2010+ extension rules that normal libraries skip) was extracted from the file. I also recalculated the whole workbook headlessly in LibreOffice and compared it with the values Excel saved: 529 of 541 numeric cells matched exactly. The other 12 are the 8 `RAND()` cells and the 4 cells that depend on the live USD/ZAR data type, which only works in Excel 365. So LibreOffice can stand in for Excel when generating test fixtures (see Section 9.6).

---

## 1. Purpose of the project

From the PDF brief (NWU, BWIA 121, participation-mark project) the calculator must cover the BWIA 111 content:

- Basic (required): interest rate conversions between `i`, `i(p)`, `i(p)/p` and `δ`; PV/AV of single investments; PV/AV of level annuities; PV/AV of annuities that increase every period.
- Additional (extra marks): simple/continuous interest; solving for payment X, capital C, term n or interest rate i; interest and capital components of a loan payment; total interest over a loan.
- Bonus: help/manuals, dynamic graphs/tables, simulations, websites.
- The brief also says that if you use a language other than Excel, you must hand in everything needed to run the program on any PC.

From the PowerPoint, each sheet is presented as its own tool (converter, single investments, annuities, loans, increasing annuities), plus a personal bonus project, "The Easy Broker" (share purchase cost in USD/ZAR and projected value).

Two slide descriptions don't match the workbook, so I followed the workbook:
- Slide 3 calls the Rate Converter a currency/exchange-rate converter. It is actually an interest-rate converter, as the PDF requires.
- Slide 7 calls Increasing Annuities a bond/coupon valuation tool. The workbook actually does growing annuities and a retirement investment-vs-withdrawal plan. There is no bond pricing.

---

## 2. Workbook anatomy

| Sheet | Type | Contents |
|---|---|---|
| `HOME` | Front end | Intro text, author block, 6 rounded-rectangle buttons that hyperlink to the other sheets. No formulas. |
| `1. RATE CONVERTER` | Front end | 7 inputs, 1 output (`O17`) |
| `2. SINGLE INVESTMENTS` | Front end | Term-from-dates block, embedded rate converter, main inputs, 3 outputs, bar chart, 2 leftover growth tables |
| `3. ANNUITIES` | Front end | Term-from-dates block, embedded converter, inputs, 16 outputs (arrears + advance) |
| `4.LOANS` | Front end | Term-from-dates block, embedded converter, inputs, period helper (T, T+1, T−1), 19 outputs |
| `5. INCREASING ANNUITIES` | Front end | Part 1: 16 outputs (every-k-th / every payment increasing, arrears + advance). Part 2: retirement plan, 5 outputs |
| `TEB` | Front end | The Easy Broker: 2 purchase calculators + FV projection, master company table, bar chart |
| `BACKROOM1` | Engine | 5 copies of a 5×5 rate-conversion grid, plus all intermediate/result calculations for sheets 2–5 |
| `BACKROOM2_TEB` | Engine/data | Country and exchange → company lists, company → share price row, live USD/ZAR data type, country return bands using `RAND()` |

Other structural elements:
- 78 defined names: 8 country lists, 8 exchange lists, 50 single-cell company prices, 4 table-column lists, and 8 broken names (`#REF!`, not used anywhere).
- 4 tables and 2 charts.
- 27 data-validation rules. All are dropdown lists; none check numeric ranges.
- 1 external link to `Left Over bit😂.xlsx`, which cannot be refreshed.
- 1 Refinitiv linked data type (USD/ZAR). Its last saved value is 17.9954, refreshed 22 Aug 2024.

Common pattern: every front-end sheet writes its inputs into `BACKROOM1`. `BACKROOM1` computes every possible answer. The front-end output cell then uses a long nested `IF(AND(type=…, type=…), cell, …)` to pick one of them. Across the workbook that is about 150 `IF` branches.

---

## 3. Module-by-module analysis

Notation: `i` is the rate used in a formula, `p` is periods per year, `n` is years or number of periods (stated each time), `X` is the installment, `s_n = ((1+i)^n − 1)/i` and `a_n = (1 − (1+i)^−n)/i`. Advance (annuity-due) values are the arrears values × `(1+i)`.

### 3.1 Rate Converter (`1. RATE CONVERTER` + `BACKROOM1!A1:F13`)

Inputs

| Cell | Label | Sample value | Validation |
|---|---|---|---|
| `P11` | From: Interest | 8.00% | none |
| `P12` | From: Period (p) | 4 | none |
| `P13` | From: Type | effective annual | list `BACKROOM1!A8:A12` (effective annual / effective periodic / nominal / simple / continous) |
| `P14` | From: Years | 6 | none |
| `R12` | To: Period (p) | 1 | none |
| `R13` | To: Type | Nominal | list `BACKROOM1!B7:F7` |
| `R14` | To: Years | 6 | none |

`R11` (To: Interest) is empty. It is linked to `BACKROOM1!D3` but never used.

Intermediate calculations: `BACKROOM1!B3:B5` and `D4:D5` copy the inputs, and `A13 = EXP(1)`. `B8:F12` is a 5×5 grid: the row is the "from" type and the column is the "to" type. Each cell holds one conversion formula. That gives 24 formulas, because continuous→continuous is empty.

Output: `O17` CONVERTED RATE. It is a 24-branch nested `IF` that returns the grid cell for the (from, to) pair, or the text `"ERROR"`. Sample result: 8.0000%.

Plain-English flow: the user enters a rate, its type and compounding frequency, then picks a target type and frequency. The backroom works out all 25 possible conversions at once, and the output cell picks the one the user asked for.

What the grid formulas actually compute:

| From \ To | Effective annual | Effective periodic | Nominal | Simple | Continuous |
|---|---|---|---|---|---|
| Effective annual | `i` | `(1+i)^(1/pₜ) − 1` | `pₜ·((1+i)^(1/pₜ) − 1)` | `i/(nₜ·pₜ)` | `LN(1+i)^n_f` |
| Effective periodic | `(1+j)^p_f − 1` | `(1+j)^(p_f/pₜ) − 1` | `pₜ·(…)` | `((1+j)^p_f − 1)/pₜ` | `LN((1+j)^p_f)` |
| Nominal | `(1+i/p_f)^12 − 1` | `(1+i/p_f)^(p_f/pₜ) − 1` | `pₜ·(…)` | `((1+i/p_f)^p_f − 1)/pₜ` | `LN(1+i)^(n_f·p_f)`* |
| Simple | `r·p_f` | `(1+r·p_f)^(1/pₜ) − 1` | `pₜ·(…)` | `r·p_f/pₜ` | `LN(1+n_f·r·p_f)` |
| Continuous | `e^(δ/(nₜ·pₜ)) − 1` | `e^(δ/(pₜ·nₜ)) − 1` | `pₜ·(…)` | `(e^δ − 1)/(nₜ·pₜ)` | missing → `"ERROR"` |

\* In the copies on sheets 2, 3 and 4 this cell is `p_f·n_f·LN(1+i/p_f)` instead. The 5 copies of the grid are not identical (see D2, D6, D7).

What this means: the formulas assume that a "simple" rate is quoted per period (so the annual simple rate is `r·p`), and they are only correct when the Years inputs are 1. If you set all Years to 1, 21 of the 25 conversions are textbook-correct. The four that are wrong even then are nominal→effective annual (a hard-coded 12), nominal→continuous (in sheets 1 and 5), continuous→effective annual (divides by `pₜ`), and continuous→continuous (missing).

### 3.2 Single Investments (`2. SINGLE INVESTMENTS` + `BACKROOM1!K4:P28`)

Inputs

| Cell | Label | Sample | Notes |
|---|---|---|---|
| `C6`,`C7`,`C8` / `E6`,`E7`,`E8` | Start and end month/year/day | 2010-01-26 → 2024-05-07 | `C5`,`E5 = DATE(y,m,d)` |
| `E10` | Years (given) | 10 | |
| `K6` | Future value | 10 000 | |
| `K7` | Present value | 2 000 | |
| `K8` | Interest rate | 10% | dropdown: `K11` (no conversion) or `E19` (converted). The chosen value is copied in, not linked |
| `K9` | Years | 10 | dropdown: `E9` (from dates) or `E10` (given) |
| `K10` | Periods (p) | 8 | |
| `K11` | Interest with no conversion | 10% | |
| `K13` | Type of outcome | FUTURE VALUE | FUTURE VALUE / PRESENT VALUE / YEARS / INTEREST / INTEREST EARNED |
| `K14` | Interest type | SIMPLE | SIMPLE / EFFECTIVE PERIODIC / EFFECTIVE ANNUAL / NOMINAL / CONTINOUS |
| `C14:C17`, `E15:E17` | Embedded converter | 7%, p 12, effective periodic → p 4, Effective periodic, years 1/1 | same logic as 3.1 |

Intermediate calculations:
- `E9 = (E5 − C5)/365`: years between the dates (Actual/365).
- `E19` is the converted rate (grid `BACKROOM1!K10:P15`). Sample: 22.5043%.
- `BACKROOM1!L24:P28` is a 5×5 result grid: interest type × {FV, PV, Years, Rate, Interest earned}.

Results grid (`i` = K8, `n` = years, `p` = periods):

| Type | FV | PV | Years | Rate |
|---|---|---|---|---|
| Simple | `PV·(1 + i·n·p)` | `FV/(1 + i·n·p)` | `(FV/PV − 1)/(i·p)` | `(FV/PV − 1)/(n·p)` |
| Effective periodic | `PV·(1+i)^(n·p)` | inverse | `log(FV/PV)/log(1+i)/p` | `(FV/PV)^(1/(n·p)) − 1` |
| Effective annual | `PV·(1+i)^n` | inverse | `log(FV/PV)/log(1+i)` | `(FV/PV)^(1/n·p) − 1` (precedence bug, D9) |
| Nominal | `PV·(1+i/p)^(n·p)` | inverse | `log(FV/PV)/log(1+i/p)/p` | `p·((FV/PV)^(1/(n·p)) − 1)` |
| Continuous | `PV·e^(i·n)` | `FV/e^(i·n)` | `ln(FV/PV)/i` | `ln(FV/PV)/n` |
| Interest earned | `L − M` (FV from PV minus PV from FV, D8). The continuous cell is empty (D10) | | | |

Outputs:
- `K16` ANSWER: FV, PV or interest earned for the chosen type, otherwise `"-"`. Sample: R 18 000.00.
- `K17` PERIOD VALUE: years, when outcome = YEARS, otherwise `"-"`.
- `K18` RATE: the rate, when outcome = INTEREST, otherwise `"-"`.
- Chart 1 is a bar chart of the FV under all 5 interest types (`BACKROOM1!L24:L28`).

Leftovers: `AO13:AP24` is a "compound" growth table that reads the external file `Left Over bit😂.xlsx`, so it cannot be recalculated. `AR13:AS24` is a "simple" table, `PV·(1 + i·n·k)` for k = 1…10. Neither is used by any output.

Plain-English flow: the user sets the term either from two dates or as a number of years, gives a rate (either directly or through the mini converter), picks what they want to solve for and how interest is applied. The backroom solves every combination and the answer cell shows the one requested.

### 3.3 Annuities (`3. ANNUITIES` + `BACKROOM1!U9:AD24`)

Inputs:
- `J6:J8`, `L6:L8`: dates, giving `L9` years (Actual/365). `L10`: years given (5).
- `Q7`: installment X (5 000).
- `Q8`: rate per period (2.0201%). Dropdown of `Q13` or `L17`, copied as a value.
- `Q9`: years (5). Dropdown of `L9`/`L10`.
- `Q10`: periods per year p (12).
- `Q11`: PV (5 200). `Q12`: FV (6 600). `Q13`: interest with no conversion (7%).
- Embedded converter `J13:L16`: 8% continuous → Effective annual, with `L14 = Q10` (the target frequency follows the annuity frequency). `L17` is the converted rate (0.6689%).

The saved `Q8` = 2.0201% matches neither dropdown option any more (`Q13` = 7%, `L17` = 0.6689%). It was picked when the converter held different inputs and has gone stale.

Outputs (`n = Q9·Q10` payments, `i = Q8` per period):

| Output | Arrears (P) | Advance (R) | Excel sample (arrears / advance) |
|---|---|---|---|
| FV | `(X·(1+i)^n − 1)/i` (bracket bug, D11) | `X·(1+i)·s_n` | 821 707.10 / 585 848.86 |
| PV | `X·a_n` | `X·(1+i)·a_n` | 172 960.26 / 176 454.28 |
| Years (given FV) | `log(1 + FV·i/X)/log(1+i)/p` | `log(1 + FV·i·(1+i)/X)…` (D12) | 0.1097 / 0.1118 |
| Years (given PV) | `log(1 − PV·i/X)/log(v)/p` | `log(1 − PV·i·(1+i)/X)…` (D12) | 0.0885 / 0.0903 |
| Installment (given FV) | `FV·i/((1+i)^n − 1)` | `… /(1+i)` | 57.47 / 56.33 |
| Installment (given PV) | `PV·i/(1 − (1+i)^−n)` | `… /(1+i)` | 150.32 / 147.35 |
| Interest (given FV) | `(X(1+i)^n − 1)/FV` (not a rate, D13) | `X(1+i)s_n·… /FV` | 251.51% / 179.32% |
| Interest (given PV) | `X(1 − v^n)/PV` (not a rate, D13) | similar | 67.19% / 68.55% |

Plain-English flow: pick the term and the periodic rate, then read the accumulated value, present value, required installment and term for payments at the end (arrears) or start (advance) of each period.

### 3.4 Loans (`4.LOANS` + `BACKROOM1!AK20:AQ44`)

Inputs:
- `H5:J7` dates → `J8` years (7.7315). `J9` years given (5).
- `R11` loan L (250 000). `R12` installment X (10 000).
- `R13` years (7.7315, dropdown `J8`/`J9`).
- `R14` rate per period (6%, dropdown of converted `J17` or `R17`).
- `R15` periods per year p (2). `R16` "During period" T (2). This is a year number.
- `R17` interest with no conversion (6%).
- Embedded converter `H13:J17`: 6% nominal p4 → Effective periodic, with `J14 = R15`. `J17` = 3.0225%.

Period helper `Q18:R20`: T, T+1 and T−1 in years, and the same in payment periods (`T·p`, `(T+1)·p`, `(T−1)·p`). In the rest of this section `t = T·p`.

Intermediate calculations in `BACKROOM1`:
- `AQ19 = L·i`.
- `AM38 = n = p·years`.
- `AM39 = L·i − X`.
- `AM41 = s_t`, `AN41 = s_(t−p)`.
- `AM43 = (L·i − X)·s_t + t·X` is the cumulative interest paid by period t. `AN43` is the same by period t−p.
- `AM44`/`AN44` are the cumulative capital paid.

Outputs (arrears `P27:P37`, advance `U27:U36`):

| Output | Formula (arrears) | Advance | Excel sample (arrears / advance) |
|---|---|---|---|
| Installment | `L/a_n` | `L/((1+i)a_n)` | 25 259.25 / 23 829.48 |
| Loan amount | `X·a_n` | `X·(1+i)·a_n` | 98 973.66 / 104 912.08 |
| Balance immediately after T | `L(1+i)^t − X·s_t` | `L(1+i)^t − X(1+i)s_t` | 271 873.08 / 269 248.31 |
| Interest part of payment t+1 | `(L·i − X)(1+i)^t + X` (= `i·B_t`) | `B_t·i` (D15) | 16 312.38 / 16 154.90 |
| Capital part of payment t+1 | `X − interest` | same | −6 312.38 / −6 154.90 |
| Number of payments needed | `ROUNDUP(−ln(1 − L·i/X)/ln(1+i))` | same formula (D14) | `#NUM!` / `#NUM!` |
| Value of last payment | `B_(N−1)·(1+i)` | `L(1+i)^(N−1) − X(1+i)s_(N−1)` | `#NUM!` / `#NUM!` |
| Capital paid during year T | `AM44 − AN44` | not provided | −11 573.08 |
| Interest paid during year T | `AM43 − AN43` | not provided | 31 573.08 |
| Total interest paid | `n·X − L` | same | −95 369.86 / −95 369.86 |
| Balance after T+1 | `years·LastPayment − X` (D16) | not provided | `#NUM!` |

The sample inputs are internally inconsistent. X = 10 000 is less than the interest per period (L·i = 15 000), so the loan never amortises: the capital parts come out negative and "payments needed" returns `#NUM!`. The workbook shows these results without any warning.

### 3.5 Increasing Annuities (`5. INCREASING ANNUITIES` + `BACKROOM1!AU1:BP38`)

Part 1 inputs:
- `I8` i per period (2%), `I9` payment X (10 000).
- `I10` N years (10), `I11` P per year (4).
- `I12` K: payments per level block (4). `I13` M: number of blocks (10).
- `I14` j: growth/inflation (5%).
- `I15` PV (400 000), `I16` FV (800 000).

Intermediate calculations: `AX7 = X·s_K`, `AX8 = X·(1+i)·s_K`, `AY7 = (1+i)^(K·M) − (1+j)^M`, `AZ7 = (1+i)^K − (1+j)`.

Part 1 outputs:
- Every K-th payment increasing (stepped): `FV = X·s_K·AY7/AZ7`, `PV = FV/(1+i)^(K·M)`, and the installment given FV or PV is the inverse. Arrears and advance.
  - Samples: FV 736 000.57 / 750 720.58; PV 333 327.60 / 339 994.15; X given FV 10 869.56 / 10 656.43; X given PV 12 000.21 / 11 764.91.
- Every payment increasing (geometric), with `n = N·P`: `FV = X·((1+i)^n − (1+j)^n)/(i − j)`, which is the PDF formula. `PV = FV/(1+i)^n`, and the installment is the inverse.
  - Samples: FV 1 610 649.68 / 1 642 862.68; PV 729 447.80 / 744 036.76; X given FV 4 966.94 / 4 869.55; X given PV 5 483.60 / 5 376.08.

Part 2 ("relationship between investments and withdrawals", a retirement plan):
- Embedded converter `E36:G41`: 9% nominal p12 → effective periodic 0.75%. Both columns use that rate.
- Investment column: single lump sum C (`J36` 15 000), inflation j (`J38` 6%), p (`J39` 12), years (`J40` 40), k (`J41` 12), m (`J42` 40).
- Withdrawal column: first withdrawal in today's money W₀ (`K36` 4 000), years to inflate (`K40` 40), k (`K41` 12), m (`K42` 20). `K39` is an input but is not used.

Part 2 outputs:
- `N36`: first withdrawal in future money, `W₁ = W₀·(1+j)^40` → 41 142.87.
- `N37`: FV of withdrawals = `W₁·s_k·((1+i)^(k·m_w) − (1+j)^m_w)/((1+i)^k − (1+j))` → 42 651 411.86.
- `N38`: PV of withdrawals at retirement = `N37/(1+i)^(k·m_w)` → 7 097 742.78.
- `N39`: FV of the lump sum = `C·(1+i)^(p·years)` → 541 648.53.
- `N40`: first monthly contribution x = `(N38 − N39)/[s_k·((1+i)^(k·m_c) − (1+j)^m_c)/((1+i)^k − (1+j))]` → 686.20.

Plain-English flow for Part 2: work out how big the first monthly contribution must be, if contributions grow with inflation every year, so that the contributions plus the lump sum are enough at retirement to fund 20 years of inflation-linked monthly withdrawals. I re-derived all five Part 2 numbers independently and they match Excel.

### 3.6 The Easy Broker (`TEB` + `BACKROOM2_TEB`)

Inputs:
- By exchange: `G5` exchange (dropdown of 8), `H5` company (dependent dropdown `INDIRECT(G5)`), `I5` share price (dropdown `INDIRECT(H5)`, a single-item list that the user must select), `I7` number of shares.
- By country: `G15` country (dropdown of 8), `H15` company, `I15` price, `I17` shares.
- Projection: `I25` years n.

Data:
- 50 companies with USD prices (`BACKROOM2_TEB` rows 18–19, duplicated in `TEB!O1:R51`).
- USD/ZAR live data type (`A23` → `B23` = 17.9954).
- Country return bands with `RAND()`, e.g. South Africa `RAND()*0.05+0.20` for 20–25% (`C28:C35`).

Outputs:
- `I8 = shares × price` (USD). `I9 = I8 × USD/ZAR` (ZAR). `I18`/`I19` are the same for the country section.
- `I26 = I19·(1 + r_country)^n`. It only uses the country section, and the result changes on every recalculation.
- Chart 2 shows the random country rates.

---

## 4. How the workbook handles edge cases and invalid inputs

1. No numeric validation. All 27 validation rules are dropdowns. Negative amounts, zero periods, rates of −100% or text typed into number cells are all accepted.
2. Errors are passed through as Excel error values:
   - `#DIV/0!` when a rate is 0 in annuity/loan formulas, when i = j in increasing annuities, or when PV or X is 0.
   - `#NUM!` for the log of a non-positive number. The sample loan already shows this: payments needed when X ≤ L·i.
   - `#VALUE!` when a number cell contains text.
   - `#REF!` in the Increasing Annuities simple-rate row.
   - `#NAME?` for the FX cell in any Excel older than 365.
3. When a lookup finds no match, the fallback differs by sheet: `"ERROR"` in the converters (continuous→continuous, or any text not in the list), `"-"` for outputs that don't apply on the single-investment sheet, and `""` for the TEB FV.
4. Blank cells are silently treated as 0:
   - The Loans converter's simple row reads blank `AJ23`/`AJ24` and returns 0%.
   - INTEREST EARNED with CONTINOUS reads blank `P28` and returns R 0.00.
5. Text matching ignores case (`'effective annual' = 'Effective annual'`), but trailing spaces matter (`'SIMPLE '`, `'NOMINAL '`, `'PRESENT VALUE '`).
6. Dropdowns copy a value instead of linking to it. `K8`, `K9`, `Q8`, `Q9`, `R13`, `R14`, `I5` and `I15` keep the value from the moment they were picked, so they go stale when the inputs upstream change.
7. Dates:
   - `DATE()` silently rolls invalid dates over (month 13 becomes January of the next year).
   - An end date before the start date gives negative years.
   - Years are `days/365` (Actual/365 Fixed), so leap days are not adjusted.
8. Fractional numbers of payments are allowed (7.7315 years × 2 = 15.46 payments). The formulas still produce values.
9. Negative capital components and negative "total interest" are shown with no warning.
10. `RAND()` is volatile, so the TEB projection changes whenever anything in the workbook is edited.
11. Broken references:
    - The Loans converter's type dropdowns (`H15`, `J15`) point at blank ranges (`H87:H91`, `J40:N40`).
    - `INDIRECT` fails for "MTN Group", "Absa Group Limited" and "Industrial&CommercialBankofChina", because their named ranges are `MTN_Group`, `Absa_Group_Limited` and `Industrial_CommercialBankofChina`.
    - The external link and 8 `#REF!` names cannot be resolved.

---

## 5. Defects and inconsistencies found

Impact is shown on the workbook's own inputs where possible.

| ID | Where | What Excel does | Correct model | Impact |
|---|---|---|---|---|
| D1 | All 5 converter grids, nominal → effective annual | `(1+i/p)^12 − 1`, with 12 hard-coded | `(1+i/p)^p − 1` | 8% nominal quarterly: 26.82% vs 8.24%. Only correct when p = 12 |
| D2 | Converter, → continuous | `LN(1+i)^n` raises the log to a power. Grids 1 and 5 also use this for nominal | `δ = ln(1+i)` | 8% EA, n = 6: 0.00002% vs 7.70% |
| D3 | Converter, continuous → effective annual | `e^(δ/(n·p)) − 1`, which is really a periodic rate | `e^δ − 1` | Annuities sample: "8% continuous → effective annual" gives 0.669% (a monthly rate) instead of 8.33% |
| D4 | Converter, continuous → continuous | Grid cell missing | `δ` | Returns `"ERROR"` |
| D5 | Converter, simple/continuous | The term n is used inconsistently (ignored in some cells, used in others) | Equivalence over n years: `1 + r·p·n = (1+i)^n` | Correct only when Years = 1 |
| D6 | Loans converter, simple → periodic/nominal/simple | References blank cells | as D5 | Always 0% |
| D7 | Increasing-annuities converter, same row | `#REF!` | as D5 | Error |
| D8 | Single investments, interest earned | `FV(from PV) − PV(from FV)` mixes two different questions | `FV(from PV) − PV` | 16 888.89 vs 16 000.00 |
| D9 | Single investments, effective annual rate | `(FV/PV)^(1/n·p) − 1` (`1/n·p` is read as `p/n`) | `(FV/PV)^(1/n) − 1` | 262.39% vs 17.46% |
| D10 | Single investments, interest earned + continuous | Blank cell | `PV·(e^(δn) − 1)` | R 0.00 |
| D11 | Annuities, FV in arrears | `(X(1+i)^n − 1)/i` (misplaced bracket) | `X((1+i)^n − 1)/i` | 821 707.10 vs 574 248.27. It even exceeds the advance FV (585 848.86), which is impossible |
| D12 | Annuities, years in advance | Multiplies by `(1+i)` instead of dividing | `n = ln(1 + FV·i/(X(1+i)))/ln(1+i)` | 0.1118 vs 0.1075 yrs (FV); 0.0903 vs 0.0867 (PV) |
| D13 | Annuities, "Interest (FV/PV)" | Ratios of values, not rates | Solve `X·s_n(i) = FV` numerically (there is no closed form) | 251.51% is meaningless |
| D14 | Loans, payments needed in advance | Reuses the arrears formula | `−ln(1 − L·d/X)/ln(1+i)`, with `d = i/(1+i)` | Wrong term for annuity-due loans |
| D15 | Loans, interest part of payment in advance | `B_t·i` | `B_t·d`: interest only accrues on the balance after the previous payment | 16 154.90 vs 15 240.47 |
| D16 | Loans, balance after T+1 | `years × last payment − X`, which has no meaning | `B_(t+1) = B_t − capital part of payment t+1` | `#NUM!` |
| D17 | Annuities/loans | The dropdown-copied rate goes stale (e.g. `Q8`) | Always use the live selected rate | Hidden wrong inputs |
| D18 | TEB | INDIRECT name mismatches, stale price copies, volatile RAND, Excel-365-only FX | Direct lookup, seeded randomness, FX fallback | 3 companies unusable |

Formulas I checked and found correct: all PV formulas; installment formulas; single-investment FV/PV/term formulas; loan balance, interest/capital split (arrears), last payment, and per-year interest/capital; both increasing-annuity models; the whole of Part 2; the TEB cost formulas.

---

## 6. Requirement coverage (PDF vs workbook)

| PDF requirement | In workbook? | Status after Python conversion |
|---|---|---|
| Rate conversion `i`, `i(p)`, `i(p)/p`, `δ` (any → any) | Yes, with D1–D7 | All 25 pairs, correct for any p and n |
| PV/AV single investment | Yes | Kept; D8–D10 fixed |
| PV/AV level annuity | Yes, with D11 | Kept; D11 fixed |
| PV/AV annuity increasing every period | Yes, correct | Kept as-is |
| Simple/continuous interest | Yes | Kept |
| Solve X / C / n / i | X, C, n yes; i only for single investments | Adds a real rate solver for annuities (D13) |
| Loan interest/capital components, total interest | Yes | Kept; D14–D16 fixed |
| Dynamic graphs/tables, simulation | 2 charts, random simulation | Kept (interactive), plus a year-by-year growth table and amortisation schedule in place of the broken leftover tables |

---

## 7. Phase 2: Excel → Python mapping

### 7.1 Inputs

| Module | Excel input(s) | Python parameter (engine) | UI widget |
|---|---|---|---|
| Converter | `P11` / `P12` / `P13` / `P14` | `value`, `from_periods`, `from_type: RateType`, `from_years` | number, int ≥ 1, select, number > 0 |
| Converter | `R12` / `R13` / `R14` | `to_periods`, `to_type`, `to_years` | same |
| All sheets | Date blocks (m/y/d ×2) + "Years (given)" + Years dropdown | `years_between(start, end)` or `years` | "Term from: dates / years" toggle + date pickers |
| Sheets 2–5 | "Interest with no conversion" + embedded converter + rate dropdown | `rate` (already chosen) | "Rate source: enter directly / convert a quoted rate" toggle. Always live, never stale |
| Single inv. | `K6`, `K7`, `K10`, `K13`, `K14` | `fv`, `pv`, `periods_per_year`, `solve_for: Outcome`, `interest_type: RateType` | numbers + 2 selects |
| Annuities | `Q7`, `Q10`, `Q11`, `Q12` + arrears/advance columns | `installment`, `periods_per_year`, `pv`, `fv`, `timing: Timing` | numbers + both timings shown side by side |
| Loans | `R11`, `R12`, `R15`, `R16` | `principal`, `installment`, `periods_per_year`, `year_T` | numbers |
| Incr. ann. P1 | `I8:I16` | `rate`, `payment`, `years`, `periods_per_year`, `k`, `m`, `growth`, `pv`, `fv` | numbers |
| Incr. ann. P2 | `J36:K42` | `RetirementInputs` dataclass | numbers in 2 columns |
| TEB | `G5`/`H5`/`I5`/`I7`, `G15`/`H15`/`I15`/`I17`, `I25`, `B23` | `exchange` / `country`, `company`, `shares`, `years`, `usd_zar` | dependent selects (the price is looked up automatically), number, FX field |

### 7.2 Calculations

| Excel | Python (single source of truth) |
|---|---|
| 5 copies of the 25-cell grid + 5 × 24-branch nested IFs | `rates.to_effective_annual()` (5 formulas) + `rates.from_effective_annual()` (5 formulas) + `rates.convert()`. Every conversion goes through the effective annual rate (hub-and-spoke), so 120 grid formulas and 5 lookups become 10 formulas. This reduces exactly to Excel's formula when Years = 1, except in the defect cells D1–D4, D6 and D7 |
| `BACKROOM1!L24:P28` + K16–K18 lookups | `single_investment.growth_factor(type, rate, years, p)`, then `future_value`, `present_value`, `interest_earned`, `solve_years`, `solve_rate`. The outcome picker becomes a small dispatch dict |
| Annuities P/R columns + `U12:V28` helpers | `annuities.fv_factor/pv_factor(i, n, timing)`, then `future_value`, `present_value`, `installment_from_fv/pv`, `term_from_fv/pv`, `rate_from_fv/pv` (bisection solver, about 15 lines, no extra dependency) |
| Loans P/U columns + `AM38:AN44` | `loans.installment`, `loan_amount`, `balance_after(t)`, `payment_split(t+1)`, `payments_needed`, `last_payment`, `year_totals(T)`, `total_interest`, `amortisation_schedule()` |
| `AX7:AZ8`, part-1 columns | `increasing_annuities.stepped_fv/pv/installment` (every k-th) and `geometric_fv/pv/installment` (every payment), including the mathematically correct i = j limit instead of `#DIV/0!` |
| `BK5:BM20` | `increasing_annuities.plan_retirement(inputs) -> RetirementResult` (5 fields = `N36:N40`) |
| `BACKROOM2_TEB`, `INDIRECT` lists, `RAND()` | `broker.MarketData` (loaded from CSV), `purchase_cost_usd`, `to_zar`, `sample_country_return(country, rng)`, `projected_value` |
| `(end − start)/365` | `dates.years_between()`: same Actual/365 convention |

### 7.3 Outputs

| Excel output | Python output |
|---|---|
| Text results `"ERROR"`, `"-"`, `""` and Excel errors `#NUM!`, `#DIV/0!` | A typed result, or a `CalculationError` with a plain-English message (e.g. "The installment is too small to cover the interest; the loan never amortises"). Outputs that don't apply are simply not shown |
| `O17`, `E19`, `L17`, `J17`, `G41` | `float` periodic/annual rate, shown as a percentage |
| `K16:K18` | the value for the selected outcome, plus a comparison table and chart across all 5 interest types (Chart 1) |
| Annuity/loan P and R/U columns | `AnnuityResult` / `LoanResult` dataclasses, shown as an arrears vs advance table |
| `N36:N40` | `RetirementResult` dataclass |
| TEB `I8`, `I9`, `I18`, `I19`, `I26`, Chart 2 | cost USD/ZAR, projected value, and the rate drawn for the country |

---

## 8. Recommended application type

Recommendation: an interactive web app built with Streamlit, backed by a pure-Python calculation package.

Why not a command-line program: the workbook is an interactive, multi-screen calculator. It has dropdowns that depend on each other, "enter dates or years" toggles, arrears and advance shown side by side, and charts. A command-line version would lose all of that, and the PDF awards marks for design, user-friendliness and dynamic graphs.

Why Streamlit fits:
1. It behaves like Excel. When any input changes, Streamlit re-runs the page, the same way Excel recalculates.
2. The folder is called "Portfolio Website", and Streamlit apps can be deployed free with a public link you can put in your portfolio. That also covers the brief's "runs on any PC" requirement: it runs in any browser.
3. It's the standard tool in data-science courses, and pages are plain Python scripts, with no HTML or JavaScript to maintain.
4. The math stays in a separate package that never imports Streamlit, so it can be tested without a UI and reused later in a CLI, notebook or desktop GUI.

| Option | Pros | Cons |
|---|---|---|
| Streamlit web app (recommended) | Interactive, charts built in, deployable link, little code | One dependency (`streamlit`) |
| Tkinter desktop app | Standard library, can be packaged as an `.exe` | Dated look, more UI code, harder to show in a portfolio |
| Command-line app | Simplest | Poor fit for a form-style multi-module calculator |

---

## 9. Proposed Python architecture

### 9.1 Project structure

```
interest-rate-calculator/
├── app.py                         # Streamlit entry point: navigation (replaces HOME buttons)
├── calculator/                    # Pure-Python financial engine (no UI imports)
│   ├── __init__.py
│   ├── types.py                   # Enums: RateType, Timing, Outcome; CalculationError
│   ├── dates.py                   # years_between() – Actual/365, as Excel
│   ├── rates.py                   # Interest-rate conversions (hub-and-spoke)
│   ├── single_investment.py       # FV / PV / term / rate / interest earned, 5 interest types
│   ├── annuities.py               # Level annuities, arrears & advance, rate solver
│   ├── loans.py                   # Amortising loans + amortisation schedule
│   ├── increasing_annuities.py    # Geometric, stepped, retirement plan
│   ├── broker.py                  # The Easy Broker logic
│   └── data/
│       ├── companies.csv          # country, exchange, company, price_usd (from BACKROOM2_TEB)
│       └── country_returns.csv    # country, low, high (from BACKROOM2_TEB!A27:C35)
├── ui/
│   ├── components.py              # Shared widgets: term input, rate-source input, result tables
│   ├── formatting.py              # R / $ / % formatting (matches Excel number formats)
│   └── pages/
│       ├── home.py                # Intro text + links (HOME sheet)
│       ├── rate_converter.py
│       ├── single_investments.py
│       ├── annuities.py
│       ├── loans.py
│       ├── increasing_annuities.py
│       └── easy_broker.py
├── tests/
│   ├── fixtures/
│   │   ├── excel_saved_values.json      # Excel's own saved results (as-shipped inputs)
│   │   └── excel_scenarios.json         # Extra scenarios recalculated from the workbook
│   ├── known_discrepancies.py           # D1–D18 registry: id, cells, reason
│   ├── test_rates.py … test_broker.py   # Unit tests + textbook identities
│   └── test_excel_parity.py             # Python vs Excel, cell by cell
├── tools/
│   ├── extract_excel_reference.py       # Reads saved values from the .xlsx
│   └── build_excel_scenarios.py         # Writes inputs into a copy, recalcs via LibreOffice
├── docs/
│   ├── excel_to_python_mapping.md       # Final version of Section 7
│   └── validation_report.md             # Generated: every comparison + discrepancy explanations
├── requirements.txt                     # streamlit ; pytest (dev) ; openpyxl (tools only)
├── run_app.bat                          # Double-click launcher for Windows
└── README.md
```

### 9.2 Design principles

- The engine is pure functions and dataclasses. Each module is small and readable, the formulas use the textbook notation from BWIA 111 (`s_n`, `a_n`, `v`, `d`, `δ`), and each function's docstring names the Excel cells it replaces.
- Enums replace magic strings, so there are no more `'SIMPLE '` vs `'Simple'` mismatches.
- Errors are raised, not returned as text. Invalid inputs (e.g. periods < 1, rate ≤ −100%) are rejected at the boundary with clear messages, and impossible questions (e.g. an installment below the interest) raise `CalculationError`, which the UI shows as a friendly warning.
- No hidden state. Rates chosen on a page are always live, which removes the stale-dropdown problem.
- Randomness is explicit. TEB uses `random.Random(seed)`, with a "re-roll" button and the rate band shown, so results can be reproduced and tested.
- FX: the default is the workbook's last value (17.9954, 22 Aug 2024), and you can edit it. An optional "fetch live rate" button uses a free public endpoint through the standard library. If that fails, it falls back to the default.
- Dependencies are minimal: `streamlit` (which brings pandas and Altair for tables and charts) and `pytest` for tests. No numpy-financial, Plotly or requests.

### 9.3 Validation strategy (Phase 4 plan)

1. Level 1, Excel's saved values: every output on every sheet is compared at the workbook's own inputs.
2. Level 2, scenario sweep: `build_excel_scenarios.py` writes new input sets into a copy of your workbook and recalculates it headlessly with LibreOffice. That engine matched Excel on all 529 deterministic cells. The sweep covers:
   - all 25 converter pairs × several (p, n) settings, including Years = 1 and ≠ 1;
   - all 25 single-investment outcome/type combinations;
   - several annuity, loan and increasing-annuity cases, including error cases.
   The results are saved as JSON, so the tests run without Excel or LibreOffice.
3. For each value the test expects one of two things:
   - Match: equal within `rel=1e-9`, which only allows for floating-point differences.
   - Documented discrepancy: the case is listed in `known_discrepancies.py`. The test then checks that Python equals an independent calculation (brute-force cash-flow sums, a period-by-period amortisation loop, conversion round-trips) and that Excel differs for the stated reason.
4. `docs/validation_report.md` is generated from the test run and lists every comparison, marked as a match or as an explained discrepancy.

Expected floating-point differences are about 1e-15 relative. They come from `LOG10` ratios vs `ln` ratios and from the extra power step in hub-and-spoke conversion. Both engines use IEEE-754 doubles.

### 9.4 How it will run

```
pip install -r requirements.txt
streamlit run app.py          # opens http://localhost:8501
pytest                        # runs the Excel-parity and unit tests
```

---

## 10. Decisions needed before coding

1. Application type: Streamlit web app (recommended), Tkinter desktop app, or CLI.
2. Handling of the Excel defects D1–D18:
   - (a) Fix and document (recommended): keep every feature, input and convention (per-period rates, arrears/advance, Actual/365), fix only the clear errors, and prove each difference in the validation report.
   - (b) Replicate the defects bug-for-bug.
   - (c) Fix, plus an "Excel-compatibility" toggle that reproduces the original numbers.
3. Leftovers: drop the broken growth tables (external link) and the unused cells, and replace them with a proper year-by-year growth table and amortisation schedule (recommended), or leave them out entirely.
