import streamlit as st

from calculator import rates
from calculator.common import RateType
from ui.components import page_header, rate_converter_inputs, results_table
from ui.formatting import pct

page_header(
    "Rate converter",
    "Two rates are equivalent when they grow money by the same amount over the same term. "
    "Every conversion goes through the effective annual rate: quoted rate → effective annual → target rate.",
    "1. RATE CONVERTER",
)

# Defaults are the workbook's saved inputs: 8% effective annual -> nominal, 6 years.
DEFAULTS = dict(value=0.08, from_type=RateType.EFFECTIVE_ANNUAL, from_periods=4, from_years=6,
                to_type=RateType.NOMINAL, to_periods=1, to_years=6)

with st.container(border=True):
    state = rate_converter_inputs("converter", defaults=DEFAULTS)

if state["converted"] is None:
    st.stop()

st.subheader("The same rate in every form")
st.caption(f"Using p = {state['to_periods']:g} periods per year and n = {state['to_years']:g} years for the target")
table = rates.equivalent_rates(state["value"], state["from_type"], state["from_periods"], state["from_years"],
                               state["to_periods"], state["to_years"])
effective = rates.to_effective_annual(state["value"], state["from_type"], state["from_periods"], state["from_years"])
results_table([{"Rate type": t.value, "Symbol": t.symbol, "Equivalent rate": pct(v)} for t, v in table.items()])
n = state["to_years"]
st.caption(f"Each of these grows R 1.00 to R {(1 + effective) ** n:,.6f} over {n:g} years.")

with st.expander("How the conversion works"):
    st.markdown("Each rate type is linked to the effective annual rate \\(i\\):")
    st.latex(r"""
\begin{aligned}
\text{Effective periodic } j &: \; 1+i = (1+j)^{p} \\
\text{Nominal } i^{(p)} &: \; 1+i = \left(1+\tfrac{i^{(p)}}{p}\right)^{p} \\
\text{Continuous } \delta &: \; 1+i = e^{\delta} \\
\text{Simple } r \text{ (per period, over } n \text{ years)} &: \; 1 + r\,p\,n = (1+i)^{n}
\end{aligned}""")
    st.markdown(
        "Simple interest does not compound, so its equivalent compound rate depends on the term \\(n\\). "
        "For every other type, the years make no difference.\n\n"
        "Fixes compared with the workbook: nominal → effective annual used a fixed 12 instead of \\(p\\) (D1); "
        "conversions to or from continuous raised the logarithm to a power (D2, D3); continuous → continuous "
        "returned `ERROR` (D4); and the term was applied inconsistently (D5). See `docs/validation_report.md`."
    )
