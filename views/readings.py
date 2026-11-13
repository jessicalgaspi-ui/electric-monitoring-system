"""Meter readings: records table + a Record dialog with a live receipt preview."""
from datetime import date

import streamlit as st

from database import PERIODS, RATES
from functions import get_household_by_id, get_last_reading, insert_meter_reading
from kit import empty, panel, receipt, show_toasts, stat, strip, toast
from theme import apply_theme, page_header
from ui import load_households, load_readings, next_period, peso, refresh_data

apply_theme()
page_header("gauge", "Meter Readings", "Look up past readings or record this month's meter value.")
show_toasts()

readings = load_readings()
households = load_households()


@st.dialog("Record meter reading", width="large")
def record_dialog():
    if households.empty:
        st.warning("Add a household first.")
        return
    n = st.session_state.get("rd_form_n", 0)
    left, right = st.columns(2, gap="large")
    with left:
        options = {f"{r['Account No.']} — {r['Homeowner']}": int(r["ID"]) for _, r in households.iterrows()}
        choice = st.selectbox("Household", list(options), key=f"rd_hh_{n}")
        hid = options[choice]
        hh = get_household_by_id(hid)
        last = get_last_reading(hid)
        if last:
            last_period, last_current, last_rate = last
            suggested_period, default_rate = next_period(last_period), last_rate
            st.caption(f"Last reading: **{last_period}** at **{last_current:,.1f} kWh** (rate {peso(last_rate)}). "
                       f"The previous reading is filled in for you.")
        else:
            last_current = 0.0
            suggested_period = date.today().strftime("%Y-%m")
            ctype = hh["connection_type"]
            try:
                default_rate = RATES[ctype][PERIODS.index(suggested_period)]
            except (ValueError, KeyError):
                default_rate = RATES.get(ctype, [12.0])[-1]
            st.caption("No readings yet for this household. Enter its starting meter value.")
        k = f"{n}_{hid}_{suggested_period}"
        c1, c2 = st.columns(2)
        period_in = c1.text_input("Billing period (YYYY-MM)", value=suggested_period, key=f"rd_period_{k}")
        reading_date = c2.date_input("Reading date", value=date.today(), key=f"rd_date_{k}")
        c3, c4 = st.columns(2)
        previous = c3.number_input("Previous (kWh)", min_value=0.0, value=float(last_current), step=1.0,
                                   format="%.1f", disabled=last is not None, key=f"rd_prev_{k}")
        current = c4.number_input("Current (kWh)", min_value=0.0, value=float(previous), step=1.0,
                                  format="%.1f", key=f"rd_curr_{k}")
        rate = st.number_input("Rate per kWh (₱)", min_value=0.01, value=float(default_rate), step=0.05,
                               format="%.2f", key=f"rd_rate_{k}")
    usage = current - previous
    with right:
        receipt("Reading preview",
                [("Household", hh["account_number"]), ("Period", period_in),
                 ("Previous", f"{previous:,.1f} kWh"), ("Current", f"{current:,.1f} kWh"),
                 ("Usage", f"{usage:,.1f} kWh"), ("Rate", peso(rate))],
                "Estimated revenue", peso(max(usage, 0) * rate))
        if usage < 0:
            st.error("Current reading cannot be lower than the previous reading.")
        if st.button("Save reading", type="primary", disabled=usage < 0, width="stretch"):
            ok, msg = insert_meter_reading(hid, period_in, previous, current, rate, reading_date.isoformat())
            if ok:
                refresh_data()
                toast(msg, "success")
                st.session_state["rd_form_n"] = n + 1
                st.rerun()
            else:
                st.error(msg)


with strip():
    with panel("records", "Records", f"{len(readings)} readings", size="xl",
               hint="Every saved reading with its usage and revenue. The totals follow your filters."):
        if st.button("Record reading", icon=":material/add:", key="open_reading"):
            record_dialog()
        if readings.empty:
            empty("meter", "No readings yet", "Use Record reading to add the first one.")
        else:
            c1, c2, c3 = st.columns([2, 1, 1])
            query = c1.text_input("Search", placeholder="Account number or homeowner name")
            ctype = c2.selectbox("Type", ["All", "Residential", "Commercial"])
            period = c3.selectbox("Billing period", ["All"] + sorted(readings["Period"].unique(), reverse=True))
            view = readings
            if query.strip():
                q = query.strip()
                view = view[view["Account"].str.contains(q, case=False, regex=False)
                            | view["Homeowner"].str.contains(q, case=False, regex=False)]
            if ctype != "All":
                view = view[view["Type"] == ctype]
            if period != "All":
                view = view[view["Period"] == period]
            m = st.columns(3)
            with m[0]:
                stat("Readings shown", f"{len(view):,}")
            with m[1]:
                stat("Total usage", f"{view['Usage (kWh)'].sum():,.0f}", "kWh")
            with m[2]:
                stat("Total revenue", peso(view["Cost (₱)"].sum()))
            display_view = view.drop(columns=["ID"]).rename(columns={"Cost (₱)": "Revenue (₱)"})
            st.dataframe(display_view, hide_index=True, width="stretch", height=300,
                         column_config={
                             "Rate (₱/kWh)": st.column_config.NumberColumn(format="₱%.2f"),
                             "Revenue (₱)": st.column_config.NumberColumn(format="₱%.2f"),
                             "Previous (kWh)": st.column_config.NumberColumn(format="%.1f"),
                             "Current (kWh)": st.column_config.NumberColumn(format="%.1f"),
                             "Usage (kWh)": st.column_config.NumberColumn(format="%.1f")})
