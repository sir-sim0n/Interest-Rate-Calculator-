from datetime import date

import pandas as pd
import streamlit as st

from calculator import single_investment as si
from calculator.common import CalculationError, RateType
from calculator.single_investment import Outcome
from ui.components import (
    RATE_TYPE_HELP,
    count_input,
    money_input,
    page_header,
    rate_input,
    results_table,
    term_input,
)
from ui.formatting import money, pct

page_header(
    "Single investments",
    "One amount invested today, left to grow. Choose what to calculate; the other values are the inputs.",
    "2. SINGLE INVESTMENTS",
)

OUTCOMES = list(Outcome)
TYPES = list(RateType)

left, right = st.columns([1, 1], gap="large")

with left:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        outcome = c1.selectbox("Calculate", OUTCOMES, index=OUTCOMES.index(Outcome.FUTURE_VALUE),
                               format_func=lambda o: o.value, key="si_outcome")
        rtype = c2.selectbox("Interest type", TYPES, index=TYPES.index(RateType.SIMPLE),
                             format_func=lambda t: t.value, key="si_type", help=RATE_TYPE_HELP)
        p = 1
        if rtype in (RateType.SIMPLE, RateType.EFFECTIVE_PERIODIC, RateType.NOMINAL):
            p = count_input("Periods per year (p)", 8, "si_p",
                            help="How often interest is added (simple: how often the per-period rate applies).")

        years = None
        if outcome is not Outcome.YEARS:
            years = term_input("si_term", default_years=10, default_start=date(2010, 1, 26),
                               default_end=date(2024, 5, 7))

        rate = None
        if outcome is not Outcome.INTEREST_RATE:
            rate = rate_input(
                "si", label="Interest rate", direct_default=0.10,
                converter_defaults=dict(value=0.07, from_type=RateType.EFFECTIVE_PERIODIC, from_periods=12,
                                        from_years=1, to_type=rtype, to_periods=p, to_years=1),
                to_type=rtype, to_periods=p, to_years=years,
                note=f"The quoted rate is converted to the {rtype.value.lower()} rate this calculation uses.",
            )
            if rate is not None:
                st.caption(f"Rate used: {pct(rate)} ({rtype.value.lower()})")

        pv = fv = None
        a, b = st.columns(2)
        if outcome is not Outcome.PRESENT_VALUE:
            pv = money_input("Present value", 2000, "si_pv")
        if outcome in (Outcome.PRESENT_VALUE, Outcome.YEARS, Outcome.INTEREST_RATE):
            fv = (b if pv is not None else a).number_input("Future value (R)", value=10000.0, min_value=0.0,
                                                           step=100.0, format="%.2f", key="si_fv")

try:
    answer = si.solve(outcome, rtype, pv=pv or 0.0, fv=fv or 0.0, rate=rate or 0.0, years=years or 0.0,
                      periods_per_year=p)
except CalculationError as exc:
    right.error(f"Cannot calculate: {exc}")
    st.stop()

# Fill in the unknown so the charts below have a complete set of values.
if outcome is Outcome.PRESENT_VALUE:
    pv = answer
elif outcome is Outcome.YEARS:
    years = answer
elif outcome is Outcome.INTEREST_RATE:
    rate = answer
final_value = si.future_value(pv, rate, rtype, years, p)

with right:
    label = {Outcome.FUTURE_VALUE: "Future value", Outcome.PRESENT_VALUE: "Present value",
             Outcome.YEARS: "Years needed", Outcome.INTEREST_RATE: f"{rtype.value} rate",
             Outcome.INTEREST_EARNED: "Interest earned"}[outcome]
    shown = {Outcome.YEARS: f"{answer:,.4f} years", Outcome.INTEREST_RATE: pct(answer)}.get(outcome, money(answer))
    with st.container(border=True):
        st.metric(label, shown)
        st.caption(f"{money(pv)} grows to {money(final_value)} in {years:,.4f} years at {pct(rate)} "
                   f"{rtype.value.lower()}" + (f" (p = {p:g})" if p != 1 else "") + ".")

    st.subheader("Same rate, different interest types")
    st.caption(f"What {money(pv)} grows to in {years:,.4f} years if {pct(rate)} were quoted as each type"
               + (f" (p = {p:g})." if p != 1 else "."))
    comparison = si.compare_interest_types(pv, rate, years, p)
    results_table([{"Interest type": t.value + (" (selected)" if t is rtype else ""), "Future value": money(v),
                    "Interest earned": money(v - pv)} for t, v in comparison.items()])

st.subheader("Growth year by year")
rows = si.growth_table(pv, rate, rtype, years, p)
if len(rows) > 1:
    g1, g2 = st.columns([3, 2], gap="large")
    g1.line_chart(pd.DataFrame({"Year": [r.year for r in rows], "Value (R)": [r.value for r in rows]}),
                  x="Year", y="Value (R)", height=300, color="#01696F")
    with g2:
        results_table([{"Year": f"{r.year:g}", "Value": money(r.value), "Interest to date": money(r.interest_to_date)}
                       for r in rows])

with st.expander("Formulas and differences from the workbook"):
    st.latex(r"""
\begin{aligned}
\text{Simple:}\quad & FV = PV\,(1 + r\,p\,n) \\
\text{Effective periodic:}\quad & FV = PV\,(1 + j)^{p\,n} \\
\text{Effective annual:}\quad & FV = PV\,(1 + i)^{n} \\
\text{Nominal:}\quad & FV = PV\,\left(1 + \tfrac{i^{(p)}}{p}\right)^{p\,n} \\
\text{Continuous:}\quad & FV = PV\,e^{\delta n}
\end{aligned}""")
    st.markdown(
        "Present value, term and rate come from rearranging these equations. Interest earned is FV − PV.\n\n"
        "- D8: the workbook subtracted the present value of the future-value input, not the actual PV.\n"
        "- D9: the effective annual rate used the exponent \\(p/n\\) instead of \\(1/n\\), an operator-precedence "
        "error.\n"
        "- D10: interest earned for continuous interest read a blank cell and showed 0."
    )
