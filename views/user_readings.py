"""Resident usage history — chart vs sector average + full reading table."""
import altair as alt
import pandas as pd
import streamlit as st

from kit import panel, show_toasts, stat, strip
from theme import TEAL, apply_theme, page_header, style_chart
from ui import load_readings

apply_theme()

if st.session_state.get("role") != "user":
    st.error("Please sign in as a resident to view this page.")
    st.stop()

household = st.session_state["household"]
page_header("chart", "My Usage History", f"Every reading recorded for {household['account_number']}")
show_toasts()

all_readings = load_readings()
my = all_readings[all_readings["Account"] == household["account_number"]].sort_values("Period")
if my.empty:
    with strip():
        with panel("empty", "No readings yet", "", size="m"):
            st.info("No readings yet for your account.")
    st.stop()

residential = all_readings[all_readings["Type"] == "Residential"]
sector_avg = residential["Usage (kWh)"].mean() if not residential.empty else 0.0
delta = my["Usage (kWh)"].mean() - sector_avg

with strip():
    with panel("compare", "Usage vs sector", "Your readings against the residential average", size="l",
               hint="Bars below the pale benchmark mean you are using less than the municipal average."):
        c = st.columns(4)
        with c[0]:
            stat("Total usage", f"{my['Usage (kWh)'].sum():,.1f}", "kWh")
        with c[1]:
            stat("Avg / month", f"{my['Usage (kWh)'].mean():,.1f}", "kWh")
        with c[2]:
            stat("Sector avg", f"{sector_avg:,.1f}", "kWh")
        with c[3]:
            stat("vs sector", f"{delta:+,.1f}", "kWh", alert=delta > 0)
        chart_df = pd.DataFrame({
            "Period": my["Period"].tolist() * 2,
            "Usage": my["Usage (kWh)"].tolist() + [sector_avg] * len(my),
            "Series": ["Your usage"] * len(my) + ["Sector average"] * len(my)})
        chart = (alt.Chart(chart_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                 .encode(x=alt.X("Period:O", title=None, axis=alt.Axis(labelAngle=-30)), xOffset="Series:N",
                         y=alt.Y("Usage:Q", title="Usage (kWh)"),
                         color=alt.Color("Series:N", title=None, scale=alt.Scale(
                             domain=["Your usage", "Sector average"], range=[TEAL, "rgba(142,202,230,0.35)"])),
                         tooltip=["Period", "Series", alt.Tooltip("Usage:Q", format=",.1f")])
                 .properties(height=300))
        st.altair_chart(style_chart(chart), theme=None)

    with panel("history", "Full history", "Latest first", size="l"):
        st.dataframe(
            my[["Period", "Previous (kWh)", "Current (kWh)", "Usage (kWh)", "Rate (₱/kWh)",
                "Cost (₱)", "Reading Date"]].iloc[::-1],
            hide_index=True, width="stretch", height=380,
            column_config={
                "Rate (₱/kWh)": st.column_config.NumberColumn(format="₱%.2f"),
                "Cost (₱)": st.column_config.NumberColumn(format="₱%.2f"),
                "Usage (kWh)": st.column_config.NumberColumn(format="%.1f")})
