"""Resident dashboard — horizontal strip, nothing below the fold.
Panels: Bill (hero) · Usage · Readings · Actions
"""
import altair as alt
import pandas as pd
import streamlit as st

from functions import fetch_disaster_incidents, get_unpaid_bills
from kit import banner, panel, pill, row, show, show_toasts, sparkline, stat, strip
from theme import TEAL, apply_theme, page_header, style_chart
from ui import load_readings, peso

apply_theme()

if st.session_state.get("role") != "user":
    st.error("Please sign in as a resident to view this page.")
    st.stop()

household = st.session_state["household"]
first_name = household["homeowner_name"].split()[0]
page_header("bolt", f"Welcome back, {first_name}",
            f"{household['account_number']}  ·  {household['address']}")
show_toasts()

all_readings = load_readings()
my = all_readings[all_readings["Account"] == household["account_number"]].copy()
if not my.empty:
    my = my.sort_values("Period")
residential = all_readings[all_readings["Type"] == "Residential"]
sector_avg = residential["Usage (kWh)"].mean() if not residential.empty else 0.0

barangay = household["address"].split(",")[0].strip()
advisories = [d for d in fetch_disaster_incidents(limit=50)
              if barangay.lower().replace("brgy.", "").strip() in d["barangay"].lower()]
if advisories:
    a = advisories[0]
    extra = f" (+{len(advisories) - 1} more)" if len(advisories) > 1 else ""
    banner(f"Grid advisory in your barangay: {a['incident_type'][:70]} · "
           f"{a['severity_level']} · {a['date_reported']}{extra}")

if my.empty:
    with strip():
        with panel("bill", "Your bill", "Nothing recorded yet", size="m"):
            st.info("No readings yet for your account. Contact your grid operator.")
    st.stop()

latest = my.iloc[-1]
unpaid = get_unpaid_bills(household["household_id"])
is_paid = latest["Period"] not in {r["billing_period"] for r in unpaid}
delta_vs = my["Usage (kWh)"].mean() - sector_avg

with strip():
    # ---- 1. Bill -----------------------------------------------------------
    with panel("bill", "Your bill", f"Billing period {latest['Period']}", size="l",
               hint="This dashboard only shows numbers for your household. "
                    "Scroll sideways, use the arrows below, or press the left/right keys."):
        left, right = st.columns([1.1, 1], gap="large")
        with left:
            stat("Amount due", peso(latest["Cost (₱)"]), hero=True, alert=not is_paid,
                 foot=f"{latest['Usage (kWh)']:,.1f} kWh at {peso(latest['Rate (₱/kWh)'])} per kWh")
            show(pill("Paid", "teal") if is_paid else pill("Outstanding", "orange", live=True))
            if not is_paid:
                if st.button("Pay now", type="primary", icon=":material/bolt:",
                             width="stretch", key="pay_now"):
                    st.switch_page("views/user_pay.py")
        with right:
            stat("Usage, last 6 periods", f"{latest['Usage (kWh)']:,.0f}", "kWh latest")
            sparkline(my.tail(6)["Usage (kWh)"].tolist(), height=90)
            c1, c2 = st.columns(2)
            with c1:
                stat("Reading date", latest["Reading Date"])
            with c2:
                stat("Account", household.get("status", "Active"))

    # ---- 2. Usage vs sector -----------------------------------------------------
    with panel("usage", "You vs the sector", "Residential average as benchmark", size="l",
               hint="Bars under the pale benchmark mean you use less than the municipal average."):
        c = st.columns(4)
        with c[0]:
            stat("Total usage", f"{my['Usage (kWh)'].sum():,.0f}", "kWh")
        with c[1]:
            stat("Avg / month", f"{my['Usage (kWh)'].mean():,.1f}", "kWh")
        with c[2]:
            stat("Sector avg", f"{sector_avg:,.1f}", "kWh")
        with c[3]:
            stat("vs sector", f"{delta_vs:+,.1f}", "kWh", alert=delta_vs > 0)
        chart_df = pd.DataFrame({
            "Period": my["Period"].tolist() * 2,
            "Usage": my["Usage (kWh)"].tolist() + [sector_avg] * len(my),
            "Series": ["Your usage"] * len(my) + ["Sector average"] * len(my)})
        bars = (alt.Chart(chart_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(x=alt.X("Period:O", title=None, axis=alt.Axis(labelAngle=-30)), xOffset="Series:N",
                        y=alt.Y("Usage:Q", title="kWh"),
                        color=alt.Color("Series:N", title=None, scale=alt.Scale(
                            domain=["Your usage", "Sector average"],
                            range=[TEAL, "rgba(142,202,230,0.35)"])),
                        tooltip=["Period", "Series", alt.Tooltip("Usage:Q", format=",.1f")])
                .properties(height=250))
        st.altair_chart(style_chart(bars), theme=None)

    # ---- 3. Recent readings -----------------------------------------------------
    with panel("readings", "Recent readings", "Latest first", size="m"):
        for _, r in my.tail(10).iloc[::-1].iterrows():
            row(r["Period"], f"{r['Usage (kWh)']:,.1f} kWh", peso(r["Cost (₱)"]))

    # ---- 4. Actions --------------------------------------------------------------
    with panel("actions", "Quick actions", "Jump to a task", size="s"):
        for title, desc, ico, target, key in [
            ("Pay a bill", "GCash, Maya or bank transfer", ":material/credit_card:", "views/user_pay.py", "pay"),
            ("My area", "Neighbours and nearby hazards", ":material/location_on:", "views/user_gis_map.py", "area"),
            ("Full history", "Every reading vs the sector", ":material/monitoring:", "views/user_readings.py", "hist"),
            ("Report outage", "Log a hazard in your barangay", ":material/warning:", "views/user_report.py", "report"),
        ]:
            with st.container(key=f"tile-{key}"):
                st.markdown(f"**{title}**")
                st.caption(desc)
                st.page_link(target, label="Open", icon=ico, width="stretch")
