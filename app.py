"""Entry point. Run with: streamlit run app.py"""
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
VIEWS_DIR = APP_ROOT / "views"
APP_ROOT_STR = str(APP_ROOT)
if APP_ROOT_STR in sys.path:
    sys.path.remove(APP_ROOT_STR)
sys.path.insert(0, APP_ROOT_STR)

import streamlit as st

from database import initialize_database

st.set_page_config(
    page_title="Electricity Monitor",
    page_icon=":material/bolt:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def _init_db():
    initialize_database()
    return True


_init_db()

# ---------------------------------------------------------------------------
# Role-based navigation (Material icons instead of emoji)
# ---------------------------------------------------------------------------
role = st.session_state.get("role")

if role == "admin":
    PAGES = [
        (VIEWS_DIR / "home.py",           "Dashboard",      ":material/dashboard:",        True),
        (VIEWS_DIR / "households.py",     "Households",     ":material/groups:",           False),
        (VIEWS_DIR / "readings.py",       "Meter Readings", ":material/speed:",            False),
        (VIEWS_DIR / "analytics_page.py", "Analytics",      ":material/monitoring:",       False),
        (VIEWS_DIR / "admin.py",          "Audit & DRRM",   ":material/shield:",           False),
        (VIEWS_DIR / "gis_map.py",        "GIS Map",        ":material/location_on:",      False),
        (VIEWS_DIR / "pdf_export.py",     "PDF Report",     ":material/picture_as_pdf:",   False),
        (VIEWS_DIR / "export.py",         "Export",         ":material/download:",         False),
    ]
elif role == "user":
    PAGES = [
        (VIEWS_DIR / "user_dashboard.py", "My Dashboard",  ":material/bolt:",              True),
        (VIEWS_DIR / "user_readings.py",  "My Readings",   ":material/monitoring:",        False),
        (VIEWS_DIR / "user_gis_map.py",   "My Area",       ":material/location_on:",       False),
        (VIEWS_DIR / "user_pay.py",       "Pay Bill",      ":material/credit_card:",       False),
        (VIEWS_DIR / "user_report.py",    "Report Outage", ":material/warning:",           False),
    ]
else:
    PAGES = [
        (VIEWS_DIR / "landing.py", "Welcome", ":material/bolt:", True),
    ]

pages = [
    st.Page(str(path), title=title, icon=icon, default=default)
    for path, title, icon, default in PAGES
]

# Top navigation bar keeps the horizontally navigable panels compact.
page = st.navigation(pages, position="top")

# ---------------------------------------------------------------------------
# Sidebar: identity + log out only (collapsed by default)
# ---------------------------------------------------------------------------
if role == "admin":
    st.sidebar.markdown("**Administrator**")
    st.sidebar.caption("Grid operator access")
elif role == "user":
    hh = st.session_state.get("household", {})
    st.sidebar.markdown(f"**{hh.get('homeowner_name', 'Resident')}**")
    st.sidebar.caption(hh.get("account_number", ""))
else:
    st.sidebar.caption("Sign in to access the platform")

if role in ("admin", "user"):
    if st.sidebar.button("Log out", icon=":material/logout:", width="stretch"):
        st.session_state.clear()
        st.rerun()

st.sidebar.divider()
st.sidebar.caption("Smart-Grid Intelligence Platform")

page.run()
