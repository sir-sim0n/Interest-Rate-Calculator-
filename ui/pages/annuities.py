from datetime import date

import streamlit as st

from calculator import annuities
from calculator.common import CalculationError, RateType, Timing
from ui.components import count_input, money_input, page_header, rate_input, results_table, show_messages, term_input
from ui.formatting import DASH, money, pct

page_header(
    "Annuities",
    "A series of equal payments. In arrears means each payment is made at the end of its period (e.g. a salary "
    "debit order), in advance means at the start (e.g. rent). Every result is shown for both.",
    "3. ANNUITIES",
)

left, right = st.columns([2, 3], gap="large")

with left:
    with st.container(border=True):
        installment = money_input("Installment per period X", 5000, "an_x")
        c1, c2 = st.columns(2)
        pv_target = c1.number_input("Present value (R)", value=5200.0, min_value=0.0, step=100.0, format="%.2f",
                                    key="an_pv", help="Used for the installment, term and rate that match this PV.")
        fv_target = c2.number_input("Future value (R)", value=6600.0, min_value=0.0, step=100.0, format="%.2f",
                                    key="an_fv", help="Used for the installment, term and rate that reach this FV.")
        p = count_input("Payments per year (p)", 12, "an_p")
        years = term_input("an_term", default_years=5, default_start=date(2010, 1, 26), default_end=date(2024, 5, 7))
        rate = rate_input(
            "an", label="Interest rate per payment period i", direct_default=0.020201340026755776,
            converter_defaults=dict(value=0.08, from_type=RateType.CONTINUOUS, from_periods=1, from_years=1),
            to_type=RateType.EFFECTIVE_PERIODIC, to_periods=p, to_years=years,
            note="Annuity formulas need the effective rate per payment period, so the quoted rate is converted "
                 "to an effective periodic rate with p = payments per year.",
        )
        n = years * p
        st.caption(f"n = {n:g} payments at {pct(rate)} per period")

try:
    results = {t: annuities.annuity_summary(installment=installment, rate=rate, years=years, periods_per_year=p,
                                            pv=pv_target, fv=fv_target, timing=t) for t in Timing}
except CalculationError as exc:
    right.error(f"Cannot calculate: {exc}")
    st.stop()

arr, adv = results[Timing.ARREARS], results[Timing.ADVANCE]


def rate_text(r):
    return DASH if r is None else pct(r)


ROWS = [
    ("Future value of the payments", "future_value", money, f"X, i, n = {n:g}"),
    ("Present value of the payments", "present_value", money, "X, i, n"),
    ("Installment to reach the future value", "installment_from_fv", money, "FV, i, n"),
    ("Installment that repays the present value", "installment_from_pv", money, "PV, i, n"),
    ("Years to reach the future value", "years_from_fv", lambda v: DASH if v is None else f"{v:,.4f}", "FV, X, i"),
    ("Years the present value lasts", "years_from_pv", lambda v: DASH if v is None else f"{v:,.4f}", "PV, X, i"),
    ("Rate per period to reach the future value", "rate_from_fv", rate_text, "FV, X, n"),
    ("Rate per period implied by the present value", "rate_from_pv", rate_text, "PV, X, n"),
]

with right:
    st.subheader("Results")
    results_table([{"Output": label, "In arrears": fmt(getattr(arr, name)), "In advance": fmt(getattr(adv, name)),
                    "Inputs": inputs} for label, name, fmt, inputs in ROWS])
    show_messages({f"{k} ({t.value.lower()})": v for t, r in results.items() for k, v in r.errors.items()})
    if arr.future_value and fv_target and fv_target < installment * n:
        st.caption(f"The future-value target ({money(fv_target)}) is less than the payments alone "
                   f"({money(installment * n)}), so the rate needed to reach it is negative.")

with st.expander("Formulas and differences from the workbook"):
    st.latex(r"""
\begin{aligned}
s_{\overline{n}|} &= \frac{(1+i)^n - 1}{i}, &\quad a_{\overline{n}|} &= \frac{1-(1+i)^{-n}}{i}, &\quad
\ddot s_{\overline{n}|} &= (1+i)\,s_{\overline{n}|}, &\quad \ddot a_{\overline{n}|} &= (1+i)\,a_{\overline{n}|} \\
FV &= X\,s_{\overline{n}|}, & PV &= X\,a_{\overline{n}|}, &
n_{FV} &= \frac{\ln\!\left(1 + \frac{FV\,i}{X}\right)}{\ln(1+i)}, & n_{PV} &= -\frac{\ln\!\left(1 - \frac{PV\,i}{X}\right)}{\ln(1+i)}
\end{aligned}""")
    st.markdown(
        "In advance, \\(X\\) is replaced by \\(X(1+i)\\) in the term formulas. The rate has no closed form, so "
        "it is found numerically by bisection (the value of an annuity rises steadily with the rate).\n\n"
        "- D11: the workbook's future value in arrears had a misplaced bracket: \\((X(1+i)^n-1)/i\\).\n"
        "- D12: the term in advance multiplied by \\((1+i)\\) where it should divide.\n"
        "- D13: the workbook's \"interest\" outputs were ratios of values, not interest rates.\n"
        "- D17: the rate chosen from the dropdown was a copied value that could go stale. Here it is always live."
    )
