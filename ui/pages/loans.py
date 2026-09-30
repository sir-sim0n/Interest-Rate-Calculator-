import math
from datetime import date

import pandas as pd
import streamlit as st

from calculator import loans
from calculator.common import CalculationError, RateType, Timing
from ui.components import page_header, rate_input, results_table, term_input
from ui.formatting import DASH, money, pct

page_header(
    "Loans",
    "A loan repaid by equal installments. See how much of each payment is interest and how much repays capital, "
    "what is still owed, and how long repayment takes.",
    "4.LOANS",
)

left, right = st.columns([2, 3], gap="large")

with left:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        principal = c1.number_input("Loan amount (R)", value=250000.0, min_value=0.0, step=1000.0, format="%.2f",
                                    key="ln_l")
        st.session_state.setdefault("ln_x", 10000.0)  # set this way so the button below can change it
        installment = c2.number_input("Installment (R)", min_value=0.0, step=100.0, format="%.2f", key="ln_x")
        c3, c4 = st.columns(2)
        p = c3.number_input("Payments per year (p)", value=2, min_value=1, step=1, key="ln_p")
        year_T = c4.number_input("Year T", value=2, min_value=0, step=1, key="ln_T",
                                 help="The year used for the balance, next-payment split and year totals.")
        years = term_input("ln_term", default_years=7.7315, default_start=date(2015, 1, 15),
                           default_end=date(2022, 10, 7), default_mode="Start and end dates", label="Loan term")
        rate = rate_input(
            "ln", label="Interest rate per payment period i", direct_default=0.06,
            converter_defaults=dict(value=0.06, from_type=RateType.NOMINAL, from_periods=4, from_years=6),
            to_type=RateType.EFFECTIVE_PERIODIC, to_periods=p, to_years=years,
            note="Loan formulas need the effective rate per payment period, so the quoted rate is converted "
                 "to an effective periodic rate with p = payments per year.",
        )
        n = years * p
        st.caption(f"n = {n:.2f} payments at {pct(rate)} per period, T = year {year_T} (after payment {year_T * p:g})")

try:
    results = {t: loans.loan_summary(principal=principal, installment_=installment, rate=rate, years=years,
                                     periods_per_year=p, year_T=year_T, timing=t) for t in Timing}
except CalculationError as exc:
    right.error(f"Cannot calculate: {exc}")
    st.stop()

arr, adv = results[Timing.ARREARS], results[Timing.ADVANCE]


def use_amortising_installment():
    st.session_state["ln_x"] = round(arr.installment, 2)


t_next = int(year_T * p) + 1
ROWS = [
    (f"Installment that repays the loan in {n:.2f} payments", "installment", money),
    (f"Loan the installment repays in {n:.2f} payments", "loan_amount", money),
    (f"Balance owed at the end of year {year_T}", "balance_at_T", money),
    (f"Interest in the next payment (payment {t_next})", "interest_next_payment", money),
    (f"Capital in the next payment (payment {t_next})", "capital_next_payment", money),
    ("Payments needed to repay the loan", "payments_needed", lambda v: DASH if v is None else f"{v:,}"),
    ("Size of the last payment", "last_payment", money),
    (f"Capital repaid during year {year_T}", "capital_in_year_T", money),
    (f"Interest paid during year {year_T}", "interest_in_year_T", money),
    ("Total interest over the term", "total_interest", money),
    (f"Balance owed at the end of year {year_T + 1}", "balance_at_T_plus_1", money),
]

with right:
    st.subheader("Results")
    results_table([{"Output": label, "In arrears": fmt(getattr(arr, name)), "In advance": fmt(getattr(adv, name))}
                   for label, name, fmt in ROWS])
    notes = [w for w in arr.warnings if w in adv.warnings]
    notes += [f"In arrears: {w}" for w in arr.warnings if w not in adv.warnings]
    notes += [f"In advance: {w}" for w in adv.warnings if w not in arr.warnings]
    if notes:
        st.warning("\n".join(f"- {w}" for w in notes))
    if arr.installment is not None and abs(arr.installment - installment) > 0.005:
        st.button(f"Use the installment that repays the loan in the term ({money(arr.installment)})",
                  on_click=use_amortising_installment)
    if any(v is not None and v < 0 for v in (arr.balance_at_T, arr.balance_at_T_plus_1)):
        st.caption("A negative balance means the loan would already be repaid by then (the installments overpay).")

st.subheader("Amortisation schedule")
timing = st.segmented_control("Payments", list(Timing), default=Timing.ARREARS, format_func=lambda t: f"In {t.value.lower()}",
                              key="ln_sched_timing") or Timing.ARREARS
repays = results[timing].payments_needed is not None
limit = results[timing].payments_needed if repays else max(1, math.ceil(n))
try:
    schedule = loans.amortisation_schedule(principal, installment, rate, p, timing, max_payments=min(limit, 600))
except CalculationError as exc:
    st.info(f"No schedule: {exc}")
    st.stop()
if not repays:
    st.caption(f"The installment never repays this loan, so the schedule shows the {limit} payments of the term only.")

s1, s2 = st.columns([1, 2], gap="large")
s1.line_chart(pd.DataFrame({"Payment": [r.payment_number for r in schedule],
                            "Balance after payment (R)": [r.closing_balance for r in schedule]}),
              x="Payment", y="Balance after payment (R)", height=320, color="#01696F")
with s2:
    st.dataframe(pd.DataFrame([{
        "Payment": r.payment_number, "Time (years)": f"{r.time_years:.2f}", "Opening balance": money(r.opening_balance),
        "Payment amount": money(r.payment), "Interest": money(r.interest), "Capital": money(r.capital),
        "Closing balance": money(r.closing_balance)} for r in schedule]), hide_index=True, height=320, width="stretch")

with st.expander("Formulas and differences from the workbook"):
    st.latex(r"""
\begin{aligned}
\text{Installment: } X &= \frac{L}{a_{\overline{n}|}} \;\;(\text{advance: } L/\ddot a_{\overline{n}|}) \\
\text{Balance after } t \text{ payments: } B_t &= L(1+i)^t - X\,s_{\overline{t}|} \;\;(\text{advance: } X\,\ddot s_{\overline{t}|}) \\
\text{Interest in payment } t+1 &= i\,B_t \;\;(\text{advance: } d\,B_t,\; d = \tfrac{i}{1+i}) \\
\text{Payments needed: } n &= \left\lceil \frac{-\ln(1 - L i / X)}{\ln(1+i)} \right\rceil \;\;(\text{advance: } L d / X)
\end{aligned}""")
    st.markdown(
        "The schedule is built payment by payment, independently of these formulas. The tests check that "
        "both approaches agree.\n\n"
        "- D14: the workbook used the arrears formula for payments needed and last payment in advance.\n"
        "- D15: interest in an advance payment used \\(i\\) instead of \\(d\\).\n"
        "- D16: \"balance after T+1\" had no financial meaning (years × last payment − X). Here it is the balance "
        "one year after T.\n"
        "- New: year-T totals are also shown for payments in advance (the workbook left them blank)."
    )
