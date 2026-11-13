"""Admin home: headline numbers, recent activity, and shortcuts."""
import streamlit as st

from kit import delta, empty, feed, panel, show, show_toasts, sparkline, stat, strip
from theme import apply_theme, page_header
from ui import load_audit_logs, load_monthly, load_summary, peso

apply_theme()
page_header("bolt", "Household Electricity Consumption Monitor",
            "Track households, meter readings and billing from one place.")
show_toasts()

stats = load_summary()
if stats is None:
    with strip():
        with panel("welcome", "Welcome", "Let's get started", size="m"):
            empty("users", "No data yet", "Register a household, then record its first meter reading.")
            st.page_link("views/households.py", label="Add a household", icon=":material/groups:", width="stretch")
    st.stop()

monthly = load_monthly()
chg = None
if len(monthly) >= 2 and monthly.iloc[-2]["Usage (kWh)"]:
    cur, prev = monthly.iloc[-1], monthly.iloc[-2]
    chg = (cur["Usage (kWh)"] - prev["Usage (kWh)"]) / prev["Usage (kWh)"] * 100

try:
    logs = load_audit_logs()
except Exception:
    logs = None

with strip():
    # ---- Overview ------------------------------------------------------------
    with panel("overview", "Overview", "Across every household", size="l",
               hint="All numbers are totals across the whole network. The line shows monthly usage."):
        left, right = st.columns([1.1, 1], gap="large")
        with left:
            stat("Total usage", f"{stats['total_consumption']:,.0f}", "kWh", hero=True,
                 foot=f"{peso(stats['total_cost'])} billed across {stats['total_readings']:,} readings")
            if chg is not None:
                show(delta(f"{chg:+.1f}% vs {monthly.iloc[-2]['Period']}", "up" if chg > 0 else "down"))
        with right:
            stat("Monthly usage", f"{monthly.iloc[-1]['Usage (kWh)']:,.0f}" if len(monthly) else "-",
                 f"kWh · {monthly.iloc[-1]['Period']}" if len(monthly) else "")
            if len(monthly):
                sparkline(monthly["Usage (kWh)"].tolist(), height=90)
        c = st.columns(3)
        with c[0]:
            stat("Households", f"{stats['total_households']:,}")
        with c[1]:
            stat("Average rate", f"{peso(stats['avg_rate'])}", "/ kWh")
        with c[2]:
            stat("Avg revenue / reading", peso(stats["mean_cost"]))

    # ---- Activity ----------------------------------------------------------------
    with panel("activity", "Recent activity", "From the audit trail", size="m"):
        if logs is None or logs.empty:
            empty("shield", "Nothing yet", "Administrative actions appear here.")
        else:
            feed([(f"{r['Action']} · {r['Target']}", str(r["Details"])[:90])
                  for _, r in logs.head(14).iterrows()])

    # ---- Shortcuts ---------------------------------------------------------------
    with panel("next", "Where to next?", "Jump straight to a task", size="s"):
        for key, title, desc, target, ico in [
            ("hh", "Households", "Manage homes and businesses", "views/households.py", ":material/groups:"),
            ("rd", "Meter readings", "Record this month's meter value", "views/readings.py", ":material/speed:"),
            ("an", "Analytics", "Trends, statistics and charts", "views/analytics_page.py", ":material/monitoring:"),
            ("ex", "Export", "Download CSV files", "views/export.py", ":material/download:"),
        ]:
            with st.container(key=f"tile-{key}"):
                st.markdown(f"**{title}**")
                st.caption(desc)
                st.page_link(target, label="Open", icon=ico, width="stretch")
