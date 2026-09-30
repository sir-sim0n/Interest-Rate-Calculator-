import streamlit as st

st.title("Interest Rate Calculator")
st.markdown(
    "Estimate how money grows over time and how loans are repaid. Enter an amount, an interest rate "
    "and a term, and each calculator finds the future value, present value, installment, term or rate "
    "you need, using simple or compound interest."
)
st.caption("Simon Motlhodimang · BWIA 121 (Interest Rate Calculator project), North-West University")

CARDS = [
    ("ui/pages/rate_converter.py", "Rate converter",
     "Convert between effective annual, effective periodic, nominal, simple and continuous rates."),
    ("ui/pages/single_investments.py", "Single investments",
     "One amount invested today. Solve for future value, present value, term, rate or interest earned."),
    ("ui/pages/annuities.py", "Annuities",
     "Level payments in arrears or in advance: values, installments, term and rate."),
    ("ui/pages/loans.py", "Loans",
     "Installments, outstanding balance, interest vs capital split and a full amortisation schedule."),
    ("ui/pages/increasing_annuities.py", "Increasing annuities",
     "Payments that grow over time, plus a retirement plan that funds inflation-linked withdrawals."),
    ("ui/pages/easy_broker.py", "The Easy Broker",
     "Price shares on eight exchanges in USD and rand, and project their value with simulated returns."),
]

for row in range(0, len(CARDS), 3):
    cols = st.columns(3)
    for col, (page, title, text) in zip(cols, CARDS[row:row + 3]):
        with col.container(border=True, height="stretch"):
            st.page_link(page, label=f"**{title}**")
            st.write(text)

st.divider()
st.subheader("About this version")
st.markdown(
    "This app is a Python rebuild of the original Excel workbook. The calculations live in a separate, "
    "tested Python package (`calculator/`), and this interface only collects inputs and shows results.\n\n"
    "- Every output was compared with the workbook: Excel's saved values plus 593 recalculated input "
    "scenarios, 1,056 values in total.\n"
    "- Where the workbook's formula is mathematically wrong, the app uses the correct formula. Each case "
    "is documented in `docs/validation_report.md`.\n"
    "- Where the workbook shows an error (for example, an installment too small to ever repay a loan), "
    "the app explains why instead."
)
