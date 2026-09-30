"""Reusable Streamlit widgets shared by the pages.

The pages only arrange inputs and show results. All financial logic lives in
the ``calculator`` package.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from calculator import rates
from calculator.common import CalculationError, RateType
from calculator.dates import years_between
from ui.formatting import pct

RATE_TYPES = list(RateType)
RATE_TYPE_HELP = (
    "Effective annual: interest per year, compounded yearly.  \n"
    "Effective periodic: interest per period (e.g. per month).  \n"
    "Nominal: annual rate compounded p times a year, i(p).  \n"
    "Simple: interest per period on the original amount only.  \n"
    "Continuous: force of interest δ."
)


# ---------------------------------------------------------------------------
# Basic inputs
# ---------------------------------------------------------------------------

def percent_input(label: str, default: float, key: str, *, help: str | None = None,
                  decimals: int = 4, min_value: float | None = None) -> float:
    """Ask for a percentage, return it as a fraction (8 -> 0.08)."""
    value = st.number_input(f"{label} (%)", value=float(default * 100), step=0.25, format=f"%.{decimals}f",
                            key=key, help=help, min_value=min_value)
    return value / 100


def money_input(label: str, default: float, key: str, *, help: str | None = None, min_value: float = 0.0) -> float:
    return st.number_input(f"{label} (R)", value=float(default), min_value=min_value, step=100.0,
                           format="%.2f", key=key, help=help)


def count_input(label: str, default: float, key: str, *, help: str | None = None, integer: bool = True,
                min_value: float = 1) -> float:
    if integer:
        return st.number_input(label, value=int(default), min_value=int(min_value), step=1, key=key, help=help)
    return st.number_input(label, value=float(default), min_value=float(min_value), step=1.0, format="%.4f",
                           key=key, help=help)


def term_input(key: str, *, default_years: float, default_start: date, default_end: date,
               default_mode: str = "Number of years", label: str = "Term") -> float:
    """Term in years, typed in or calculated from two dates (Actual/365, like Excel's (end-start)/365)."""
    modes = ["Number of years", "Start and end dates"]
    mode = st.radio(label, modes, index=modes.index(default_mode), horizontal=True, key=f"{key}_mode")
    if mode == "Number of years":
        return st.number_input("Years", value=float(default_years), min_value=0.0, step=1.0, format="%.4f",
                               key=f"{key}_years")
    c1, c2 = st.columns(2)
    start = c1.date_input("Start date", value=default_start, key=f"{key}_start", format="YYYY-MM-DD")
    end = c2.date_input("End date", value=default_end, key=f"{key}_end", format="YYYY-MM-DD")
    try:
        years = years_between(start, end)
    except CalculationError as exc:
        st.error(str(exc))
        st.stop()
    st.caption(f"Term = {years:.4f} years (days ÷ 365)")
    return years


# ---------------------------------------------------------------------------
# Rate input with the optional embedded converter
# ---------------------------------------------------------------------------

def rate_converter_inputs(key: str, *, defaults: dict, to_type: RateType | None = None,
                          to_periods: float | None = None, to_years: float | None = None,
                          compact: bool = False) -> dict:
    """The FROM/TO block that each Excel sheet embeds.

    ``to_type`` / ``to_periods`` / ``to_years`` given = locked to what the
    calculation on the page needs (shown as text); otherwise the user picks
    them. ``compact`` uses two columns instead of four, for narrow panels.
    Returns every setting plus ``converted`` (None, with the reason shown,
    when the inputs are invalid).
    """
    def grid():
        return st.columns(2) + st.columns(2) if compact else st.columns(4)

    st.markdown("**Convert from**")
    c = grid()
    value = c[0].number_input("Quoted rate (%)", value=float(defaults["value"] * 100), step=0.25, format="%.4f",
                              key=f"{key}_cv_value") / 100
    from_type = c[1].selectbox("Rate type", RATE_TYPES, index=RATE_TYPES.index(defaults["from_type"]),
                               format_func=lambda t: t.value, key=f"{key}_cv_from_type", help=RATE_TYPE_HELP)
    from_periods = c[2].number_input("Periods per year (p)", value=float(defaults["from_periods"]),
                                     min_value=0.0001, step=1.0, key=f"{key}_cv_from_p")
    from_years = c[3].number_input("Years (n)", value=float(defaults["from_years"]), min_value=0.0001, step=1.0,
                                   key=f"{key}_cv_from_n",
                                   help="Only matters for simple interest, where the equivalent rate depends on the term.")

    locked = []
    open_fields = sum(x is None for x in (to_type, to_periods, to_years))
    if open_fields or not compact:
        st.markdown("**Convert to**")
        d = grid()
        slots = iter(d[1:] if not compact else d)
    if to_type is None:
        to_type = next(slots).selectbox("Rate type ", RATE_TYPES, index=RATE_TYPES.index(defaults["to_type"]),
                                        format_func=lambda t: t.value, key=f"{key}_cv_to_type")
    else:
        locked.append(to_type.value.lower())
    if to_periods is None:
        to_periods = next(slots).number_input("Periods per year (p) ", value=float(defaults["to_periods"]),
                                              min_value=0.0001, step=1.0, key=f"{key}_cv_to_p")
    else:
        locked.append(f"p = {to_periods:g}")
    if to_years is None:
        to_years = next(slots).number_input("Years (n) ", value=float(defaults["to_years"]), min_value=0.0001,
                                            step=1.0, key=f"{key}_cv_to_n")
    elif to_type is RateType.SIMPLE:
        locked.append(f"n = {to_years:g} years")
    if locked:
        st.caption("Target: " + ", ".join(locked) + " (set by this calculator)")

    state = dict(value=value, from_type=from_type, from_periods=from_periods, from_years=from_years,
                 to_type=to_type, to_periods=to_periods, to_years=to_years, converted=None)
    out = st if compact else d[0]
    try:
        state["converted"] = rates.convert_rate(value, from_type, to_type, from_periods, to_periods,
                                                from_years, to_years)
    except CalculationError as exc:
        out.error(str(exc))
        return state
    out.metric("Converted rate", pct(state["converted"]))
    return state


def rate_input(key: str, *, label: str, direct_default: float, converter_defaults: dict,
               default_mode: str = "Enter the rate", to_type: RateType | None = None,
               to_periods: float | None = None, to_years: float | None = None, note: str | None = None) -> float:
    """The rate used by a calculator: typed in directly, or converted from a quoted rate.

    This replaces Excel's "USE INTEREST FROM CONVERTER / INTEREST WITH NO
    CONVERSION" dropdown. The rate is read live, so it can't go stale (D17).
    """
    modes = ["Enter the rate", "Convert a quoted rate"]
    mode = st.radio(label, modes, index=modes.index(default_mode), horizontal=True, key=f"{key}_rate_mode")
    if mode == "Enter the rate":
        return percent_input(label, direct_default, f"{key}_rate_direct")
    with st.container(border=True):
        if note:
            st.caption(note)
        converted = rate_converter_inputs(key, defaults=converter_defaults, to_type=to_type,
                                          to_periods=to_periods, to_years=to_years, compact=True)["converted"]
    if converted is None:
        st.stop()
    return converted


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def show_messages(errors: dict[str, str] | None = None, warnings: list[str] | None = None) -> None:
    for w in dict.fromkeys(warnings or []):
        st.warning(w)
    for msg in dict.fromkeys((errors or {}).values()):
        st.info(msg)


def results_table(rows: list[dict], *, hide_index: bool = True) -> None:
    """Show pre-formatted result rows as a static table."""
    height = 35 * (len(rows) + 1) + 3  # show every row without an inner scrollbar
    st.dataframe(pd.DataFrame(rows), hide_index=hide_index, width="stretch", height=height)


def page_header(title: str, subtitle: str, excel_sheet: str) -> None:
    st.title(title)
    st.markdown(subtitle)
    st.caption(f"Converted from the Excel sheet {excel_sheet}")
