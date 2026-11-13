"""Shared helpers for the Streamlit pages.

Two responsibilities:
  1. Column-order constants that must stay in sync with functions.py — every
     DataFrame loader renames raw sqlite3.Row objects using these lists.
  2. Cached data loaders (@st.cache_data with a 30 s TTL). Call refresh_data()
     after any write so the next page load sees fresh numbers.

Also provides the flash-message pattern (survives st.rerun()).
"""
import pandas as pd
import streamlit as st

from analytics import (
    get_connection_totals,
    get_monthly_totals,
    get_summary_statistics,
)
from functions import (
    fetch_all_households,
    fetch_all_readings,
    fetch_audit_logs,
    fetch_disaster_incidents,
    get_highest_consumer,
)

# ---------------------------------------------------------------------------
# Column-order contracts — MUST match functions.py return order
# ---------------------------------------------------------------------------
HOUSEHOLD_COLUMNS = ["ID", "Account No.",
                     "Homeowner", "Address", "Type", "Status"]

READING_COLUMNS = [
    "ID", "Account", "Homeowner", "Period",
    "Previous (kWh)", "Current (kWh)", "Usage (kWh)",
    "Rate (₱/kWh)", "Cost (₱)", "Reading Date", "Type",
]

AUDIT_COLUMNS = ["Log ID", "Timestamp", "Action", "Target", "Details"]

DISASTER_COLUMNS = ["ID", "Date Reported", "Barangay", "Incident", "Severity"]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def peso(value):
    return f"₱{value:,.2f}"


def next_period(period):
    """'2026-09' -> '2026-10'"""
    year, month = int(period[:4]), int(period[5:7]) + 1
    if month > 12:
        year, month = year + 1, 1
    return f"{year}-{month:02d}"


def suggest_next_account(households_df):
    """Returns 'ACC-####' one above the highest existing account number."""
    nums = [int(a[4:])
            for a in households_df["Account No."] if a[4:].isdigit()]
    return f"ACC-{(max(nums) + 1) if nums else 8001}"


# ---------------------------------------------------------------------------
# Cached data loaders — cleared after every successful write
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def load_households():
    return pd.DataFrame(fetch_all_households(), columns=HOUSEHOLD_COLUMNS)


@st.cache_data(ttl=30, show_spinner=False)
def load_readings():
    return pd.DataFrame(fetch_all_readings(), columns=READING_COLUMNS)


@st.cache_data(ttl=30, show_spinner=False)
def load_summary():
    return get_summary_statistics()


@st.cache_data(ttl=30, show_spinner=False)
def load_monthly():
    return pd.DataFrame(
        get_monthly_totals(),
        columns=["Period", "Usage (kWh)", "Cost (₱)"],
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_connection_totals():
    return pd.DataFrame(
        get_connection_totals(),
        columns=["Type", "Usage (kWh)", "Cost (₱)"],
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_highest_consumer():
    row = get_highest_consumer()
    return tuple(row) if row is not None else None


@st.cache_data(ttl=30, show_spinner=False)
def load_audit_logs():
    return pd.DataFrame(fetch_audit_logs(), columns=AUDIT_COLUMNS)


@st.cache_data(ttl=30, show_spinner=False)
def load_disaster_incidents():
    return pd.DataFrame(fetch_disaster_incidents(), columns=DISASTER_COLUMNS)


def refresh_data():
    """Call after any write so every page shows fresh data."""
    st.cache_data.clear()


# ---------------------------------------------------------------------------
# Flash messages — survive st.rerun()
# ---------------------------------------------------------------------------
def flash(message, kind="success"):
    st.session_state.setdefault("_toasts", []).append((kind, message))


def show_flash():
    pass  # kit.show_toasts() drains the queue inside apply_theme()
