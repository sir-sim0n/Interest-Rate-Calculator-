"""Interest Rate Calculator: Streamlit entry point.

Run with:   streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="Interest Rate Calculator", page_icon=":material/calculate:", layout="wide")

PAGES = {
    "": [
        st.Page("ui/pages/home.py", title="Home", icon=":material/home:", default=True),
    ],
    "Calculators": [
        st.Page("ui/pages/rate_converter.py", title="Rate converter", icon=":material/swap_horiz:"),
        st.Page("ui/pages/single_investments.py", title="Single investments", icon=":material/savings:"),
        st.Page("ui/pages/annuities.py", title="Annuities", icon=":material/event_repeat:"),
        st.Page("ui/pages/loans.py", title="Loans", icon=":material/account_balance:"),
        st.Page("ui/pages/increasing_annuities.py", title="Increasing annuities", icon=":material/trending_up:"),
    ],
    "Investing": [
        st.Page("ui/pages/easy_broker.py", title="The Easy Broker", icon=":material/candlestick_chart:"),
    ],
}

st.navigation(PAGES).run()
