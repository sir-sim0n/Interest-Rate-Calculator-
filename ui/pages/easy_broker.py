import random

import pandas as pd
import streamlit as st

from calculator import broker
from calculator.common import CalculationError
from ui.components import page_header, results_table
from ui.formatting import money, pct, usd

page_header(
    "The Easy Broker",
    "Price a share purchase on eight stock exchanges in US dollars and rand, then project its value using a "
    "simulated annual return for the company's country.",
    "TEB",
)

data = broker.market_data()

# -- session state: exchange rate and simulated returns ----------------------
st.session_state.setdefault("teb_fx", broker.DEFAULT_USD_ZAR)
st.session_state.setdefault("teb_fx_note", f"Rate saved in the workbook on {broker.DEFAULT_USD_ZAR_DATE:%d %B %Y}.")
st.session_state.setdefault("teb_returns", dict(broker.WORKBOOK_RETURNS))
st.session_state.setdefault("teb_returns_note", "Returns saved in the workbook.")


def fetch_fx():
    try:
        rate, as_of = broker.fetch_live_usd_zar()
    except CalculationError as exc:
        st.session_state["teb_fx_note"] = f"{exc} Keeping the previous rate."
        return
    st.session_state["teb_fx"] = rate
    st.session_state["teb_fx_note"] = f"Live ECB reference rate for {as_of} (via frankfurter.dev)."


def resimulate(seed=None):
    rng = random.Random(seed)
    st.session_state["teb_returns"] = broker.sample_all_returns(data, rng)
    st.session_state["teb_returns_note"] = "Newly simulated returns (uniform within each country's band)."


with st.container(border=True):
    f1, f2, f3 = st.columns([1, 1, 2], vertical_alignment="bottom")
    usd_zar = f1.number_input("USD/ZAR exchange rate", min_value=0.0001, step=0.01, format="%.4f", key="teb_fx")
    f2.button("Fetch live rate", on_click=fetch_fx, icon=":material/sync:")
    f3.caption(st.session_state["teb_fx_note"])

left, right = st.columns(2, gap="large")

# -- A: buy on an exchange ----------------------------------------------------------
with left:
    st.subheader("Buy on a stock exchange")
    with st.container(border=True):
        exchanges = data.exchanges()
        exchange = st.selectbox("Stock exchange", exchanges, index=exchanges.index("SSE"), key="teb_ex",
                                format_func=lambda e: f"{e} – {data.companies_on_exchange(e)[0].exchange_name}")
        options = data.companies_on_exchange(exchange)
        names = [c.name for c in options]
        company = options[names.index("Huawei")] if "Huawei" in names else options[0]
        company = st.selectbox("Company", options, index=options.index(company), key=f"teb_ex_co_{exchange}",
                               format_func=lambda c: f"{c.name} ({usd(c.price_usd)})")
        shares = st.number_input("Number of shares", value=10, min_value=0, step=1, key="teb_ex_shares")
    cost_usd = broker.purchase_cost_usd(company.price_usd, shares)
    a1, a2 = st.columns(2)
    a1.metric("Cost in USD", usd(cost_usd))
    a2.metric("Cost in rand", money(broker.to_zar(cost_usd, usd_zar)))

# -- B: buy in a country and project ------------------------------------------------
with right:
    st.subheader("Buy in a country and project")
    with st.container(border=True):
        countries = data.countries()
        country = st.selectbox("Country", countries, index=countries.index("China"), key="teb_country")
        options = data.companies_in_country(country)
        names = [c.name for c in options]
        company_b = options[names.index("Huawei")] if "Huawei" in names else options[0]
        company_b = st.selectbox("Company ", options, index=options.index(company_b), key=f"teb_c_co_{country}",
                                 format_func=lambda c: f"{c.name} ({usd(c.price_usd)})")
        c1, c2 = st.columns(2)
        shares_b = c1.number_input("Number of shares ", value=6, min_value=0, step=1, key="teb_c_shares")
        years = c2.number_input("Years to hold", value=5.0, min_value=0.0, step=1.0, key="teb_years")
    cost_b_usd = broker.purchase_cost_usd(company_b.price_usd, shares_b)
    cost_b_zar = broker.to_zar(cost_b_usd, usd_zar)
    annual = st.session_state["teb_returns"][country]
    b1, b2 = st.columns(2)
    b1.metric("Cost in USD", usd(cost_b_usd))
    b2.metric("Cost in rand", money(cost_b_zar))
    st.metric(f"Projected value after {years:g} years", money(broker.projected_value(cost_b_zar, annual, years)))
    band = data.band(country)
    st.caption(f"Projected at {pct(annual, 2)} a year, simulated from {country}'s {band.label} band.")

# -- Simulated returns by country --------------------------------------------------
st.subheader("Simulated annual returns by country")
r1, r2 = st.columns([3, 2], gap="large")
returns = st.session_state["teb_returns"]
chart = pd.DataFrame({"Country": list(returns), "Annual return (%)": [v * 100 for v in returns.values()]})
r1.bar_chart(chart, x="Country", y="Annual return (%)", height=320, color="#01696F", horizontal=True)
with r2:
    results_table([{"Country": c, "Band": data.band(c).label, "Simulated return": pct(v, 2)} for c, v in returns.items()])
    st.button("Simulate new returns", on_click=resimulate, icon=":material/casino:")
    st.caption(st.session_state["teb_returns_note"])

with st.expander("How this works, and differences from the workbook"):
    st.markdown(
        "- Cost in USD = shares × price. Cost in rand = cost in USD × USD/ZAR. "
        "Projected value = cost in rand × (1 + r)^years.\n"
        "- Each country's return r is drawn uniformly from its band, as Excel's `RAND()` did. Excel drew new "
        "returns on every edit. Here they only change when you ask, so results stay stable while you explore.\n"
        "- The company list and prices are in `calculator/data/companies.csv`, the return bands in "
        "`country_returns.csv`. Edit them to update the data.\n"
        "- D18: in the workbook, MTN Group, Absa Group Limited and Industrial & Commercial Bank of China could "
        "not be priced because their range names didn't match. They work here. Excel's live exchange rate "
        "needed a Microsoft 365 data type; here it is an editable number with an optional live fetch."
    )
