import pandas as pd
import streamlit as st

from calculator import increasing_annuities as ia
from calculator.common import CalculationError, RateType, Timing
from ui.components import count_input, money_input, page_header, percent_input, rate_input, results_table
from ui.formatting import money, pct

page_header(
    "Increasing annuities",
    "Payments that grow over time, for example contributions that rise with your salary, or withdrawals "
    "that keep pace with inflation.",
    "5. INCREASING ANNUITIES",
)

part1, part2 = st.tabs(["Part 1: increasing annuities", "Part 2: retirement plan"])

# ---------------------------------------------------------------------------
# Part 1
# ---------------------------------------------------------------------------
with part1:
    left, right = st.columns([1, 1], gap="large")
    with left:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                payment = money_input("First payment X", 10000, "ia_x")
                rate = percent_input("Interest per period i", 0.02, "ia_i")
                pv = money_input("PV target", 400000, "ia_pv")
            with c2:
                growth = percent_input("Payment growth j", 0.05, "ia_j",
                                       help="Each increase multiplies the payment by (1 + j).")
                fv = money_input("FV target", 800000, "ia_fv")
            st.markdown("**Every k-th payment increasing**")
            c3, c4 = st.columns(2)
            with c3:
                k = count_input("Payments per block k", 4, "ia_k", help="Payments stay level for k periods, then rise.")
            with c4:
                m = count_input("Number of blocks m", 10, "ia_m")
            st.markdown("**Every payment increasing**")
            c5, c6 = st.columns(2)
            with c5:
                years = count_input("Years N", 10, "ia_n")
            with c6:
                periods = count_input("Periods per year P", 4, "ia_p")

    try:
        stepped = {t: ia.stepped_summary(payment=payment, rate=rate, growth=growth, k=k, m=m, pv=pv, fv=fv, timing=t)
                   for t in Timing}
        geometric = {t: ia.geometric_summary(payment=payment, rate=rate, growth=growth, years=years,
                                             periods_per_year=periods, pv=pv, fv=fv, timing=t) for t in Timing}
    except CalculationError as exc:
        right.error(f"Cannot calculate: {exc}")
    else:
        ROWS = [("Future value of the payments", "future_value"), ("Present value of the payments", "present_value"),
                ("First payment to reach the FV target", "installment_from_fv"),
                ("First payment to fund the PV target", "installment_from_pv")]
        with right:
            st.markdown(f"**Every k-th payment increasing** · {k * m} payments, rising every {k}")
            results_table([{"Output": label, "In arrears": money(getattr(stepped[Timing.ARREARS], name)),
                             "In advance": money(getattr(stepped[Timing.ADVANCE], name))} for label, name in ROWS])
            st.markdown(f"**Every payment increasing** · {years * periods} payments, each {pct(growth, 2)} larger")
            results_table([{"Output": label, "In arrears": money(getattr(geometric[Timing.ARREARS], name)),
                             "In advance": money(getattr(geometric[Timing.ADVANCE], name))} for label, name in ROWS])

        st.subheader("Payment pattern")
        n_step, n_geo = int(k * m), int(years * periods)
        count = max(n_step, n_geo)
        pattern = pd.DataFrame({
            "Payment": range(1, count + 1),
            "Every k-th payment": [payment * (1 + growth) ** ((t - 1) // k) if t <= n_step else None
                                              for t in range(1, count + 1)],
            "Every payment": [payment * (1 + growth) ** (t - 1) if t <= n_geo else None
                                         for t in range(1, count + 1)],
        })
        st.line_chart(pattern, x="Payment", y=["Every k-th payment", "Every payment"],
                      color=["#01696F", "#A84B2F"], height=280)

    with st.expander("Formulas"):
        st.latex(r"""
\begin{aligned}
\text{Every payment increasing:}\quad FV &= X\,\frac{(1+i)^n - (1+j)^n}{i - j}, \quad n = N P
\qquad (i = j:\; FV = n X (1+i)^{n-1}) \\
\text{Every k-th payment increasing:}\quad FV &= X\,s_{\overline{k}|}\,
\frac{(1+i)^{km} - (1+j)^m}{(1+i)^k - (1+j)} \\
PV &= FV\,(1+i)^{-n}, \qquad \text{advance} = (1+i)\times\text{arrears}
\end{aligned}""")
        st.markdown("The workbook shows `#DIV/0!` when the growth equals the interest; the app uses the limit "
                    "instead.")

# ---------------------------------------------------------------------------
# Part 2
# ---------------------------------------------------------------------------
with part2:
    st.markdown(
        "Save with contributions that rise each year with inflation, on top of a lump sum invested today, so "
        "that at retirement you can fund withdrawals that also rise with inflation."
    )
    left, right = st.columns([1, 1], gap="large")
    with left:
        with st.container(border=True):
            lump_p = count_input("Compounding periods per year (p)", 12, "rp_p")
            rate = rate_input(
                "rp", label="Interest rate per period i", direct_default=0.0075, default_mode="Convert a quoted rate",
                converter_defaults=dict(value=0.09, from_type=RateType.NOMINAL, from_periods=12, from_years=1),
                to_type=RateType.EFFECTIVE_PERIODIC, to_periods=lump_p, to_years=1,
            )
            inflation = percent_input("Inflation per year (j)", 0.06, "rp_j")
            st.markdown("**Saving**")
            c1, c2 = st.columns(2)
            lump_sum = c1.number_input("Lump sum today (R)", value=15000.0, min_value=0.0, step=1000.0,
                                       format="%.2f", key="rp_lump")
            lump_years = c2.number_input("Years until retirement (n)", value=40.0, min_value=0.0, step=1.0, key="rp_n")
            c3, c4 = st.columns(2)
            ck = c3.number_input("Contributions per year (k)", value=12, min_value=1, step=1, key="rp_ck")
            cm = c4.number_input("Years of contributions (m)", value=40, min_value=1, step=1, key="rp_cm")
            st.markdown("**Retirement**")
            c5, c6 = st.columns(2)
            w0 = c5.number_input("First withdrawal today (R)", value=4000.0, min_value=0.0, step=100.0,
                                 format="%.2f", key="rp_w0",
                                 help="In today's money. It is inflated at j a year until withdrawals start.")
            inflate_years = c6.number_input("Years until it starts", value=40.0, min_value=0.0, step=1.0,
                                            key="rp_wy")
            c7, c8 = st.columns(2)
            wk = c7.number_input("Withdrawals per year (k)", value=12, min_value=1, step=1, key="rp_wk")
            wm = c8.number_input("Years of withdrawals (m)", value=20, min_value=1, step=1, key="rp_wm")

    try:
        plan = ia.plan_retirement(ia.RetirementInputs(
            rate=rate, inflation=inflation, lump_sum=lump_sum, lump_sum_periods_per_year=lump_p,
            lump_sum_years=lump_years, contribution_k=ck, contribution_m=cm, first_withdrawal_today=w0,
            years_to_inflate=inflate_years, withdrawal_k=wk, withdrawal_m=wm))
    except CalculationError as exc:
        right.error(f"Cannot calculate: {exc}")
    else:
        with right:
            with st.container(border=True):
                st.metric("First contribution needed", money(plan.first_contribution))
                st.caption(f"Rising by {pct(inflation, 2)} every {ck} contributions, for {cm} years.")
            st.subheader("How it is worked out")
            results_table([
                {"Step": "1. First withdrawal, inflated to retirement", "Value": money(plan.first_withdrawal)},
                {"Step": "2. Value of all withdrawals at retirement", "Value": money(plan.withdrawals_pv)},
                {"Step": "3. Lump sum grown to retirement", "Value": money(plan.lump_sum_fv)},
                {"Step": "4. Gap the contributions must fill (2 − 3)",
                 "Value": money(plan.withdrawals_pv - plan.lump_sum_fv)},
                {"Step": "Value of all withdrawals at the end of retirement", "Value": money(plan.withdrawals_fv)},
            ])
            if plan.first_contribution < 0:
                st.info("The lump sum alone already covers the withdrawals, so no contributions are needed.")
