"""Landing page: welcome panel + one access panel (Sign in / Create account).

Sets st.session_state["role"] on successful authentication or registration,
which app.py uses to switch the entire navigation.

Admin credentials live in .streamlit/secrets.toml under [admin] (username, password).
Never put the real password in source code or on this page.
"""
import streamlit as st

from functions import (authenticate_resident, fetch_demo_accounts,
                       log_audit_event, register_account)
from kit import feed, panel, show_toasts, strip
from theme import apply_theme, page_header
from ui import load_households, suggest_next_account

ADMIN_USERNAME = st.secrets["admin"]["username"]
ADMIN_PASSWORD = st.secrets["admin"]["password"]

apply_theme()
page_header("bolt", "Smart-Grid Intelligence Platform",
            "Echague & Santiago City — Provincial Telemetry Network")
show_toasts()


def _signed_in(role, **extra):
    st.cache_data.clear()
    st.session_state["role"] = role
    for k, v in extra.items():
        st.session_state[k] = v
    st.rerun()


with strip():
    # ---- Welcome -----------------------------------------------------------
    with panel("welcome", "Welcome",
               "One place for household's readings and billing", size="m"):
        st.html(
            '<div class="hero-copy">'
            '<div class="hero-title">'
            'Your grid. One screen. Full control.</div>'
            '<div class="hero-description">'
            'Smart-Grid Intelligence Platform brings billing, analytics, GIS mapping, and DRRM response '
            'into a single auditable control room — for residents and operators alike. No more juggling '
            'six systems to run one grid. Every reading, every bill, every incident, in one place.'
            '</div></div>'
        )
        feed([("Residents", "Check bills, monitor usage, pay online and report outages"),
              ("Administrators", "Manage households, analyze consumption and map disasters that might effect eclectricity grids")])
        st.caption(
            "Domingo abegail · Lagmay Jessica · Delemendo Aldwyn · De Vera Kristine "
            "· Isabela State University BSDSA · Smart-Grid Intelligence Platform v3.1")

    # ---- Access ------------------------------------------------------------
    with panel("access", "Access", "Sign in or create a resident account", size="m"):
        mode = st.segmented_control("Mode", ["Sign in", "Create account"], default="Sign in",
                                    key="landing_mode", label_visibility="collapsed") or "Sign in"

        if mode == "Sign in":
            who = st.segmented_control("Role", ["Resident", "Administrator"], default="Resident",
                                       key="landing_role", label_visibility="collapsed") or "Resident"
            if who == "Resident":
                with st.form("resident_login"):
                    acc = st.text_input("Account number", placeholder="ACC-8001",
                                        help="Your account number from your electricity bill")
                    pwd = st.text_input(
                        "Password", type="password", placeholder="••••••••")
                    submitted = st.form_submit_button(
                        "Sign in as resident", type="primary", width="stretch")
                if submitted:
                    ok, result = authenticate_resident(acc, pwd)
                    if ok:
                        log_audit_event("RESIDENT_LOGIN", result["account_number"],
                                        f"Resident {result['homeowner_name']} signed in")
                        _signed_in(
                            "user", household_id=result["household_id"], household=result)
                    else:
                        st.error(result)
            else:
                with st.form("admin_login"):
                    username = st.text_input("Username", placeholder="admin")
                    password = st.text_input(
                        "Password", type="password", placeholder="••••••••")
                    submitted = st.form_submit_button(
                        "Sign in as administrator", type="primary", width="stretch")
                if submitted:
                    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                        log_audit_event("ADMIN_LOGIN", username,
                                        "Administrator signed in")
                        _signed_in("admin")
                    else:
                        st.error("Invalid username or password.")
        else:
            with st.form("resident_register"):
                a1, a2 = st.columns(2)
                homeowner_name = a1.text_input(
                    "Homeowner name", placeholder="Maria Santos",
                    help="Your full name exactly as it appears on your bill")
                account_number = a2.text_input(
                    "Account number", value=suggest_next_account(load_households()),
                    help="Choose a new, unused account number. Existing accounts must sign in instead.")
                address = st.text_input(
                    "Address", placeholder="Brgy. Baluarte, Santiago City")
                c1, c2 = st.columns(2)
                connection_type = c1.selectbox(
                    "Connection type", ["Residential", "Commercial"])
                st.caption(
                    "Enter the household's verified GPS coordinates (for example, from a map pin).")
                lat_col, lon_col = st.columns(2)
                latitude = lat_col.text_input(
                    "Latitude", placeholder="e.g. 16.700000")
                longitude = lon_col.text_input(
                    "Longitude", placeholder="e.g. 121.670000")
                p1, p2 = st.columns(2)
                password = p1.text_input(
                    "Password", type="password", placeholder="At least 6 characters")
                confirm = p2.text_input(
                    "Confirm password", type="password", placeholder="Repeat password")
                submitted = st.form_submit_button(
                    "Create account & sign in", type="primary", width="stretch")
            if submitted:
                ok, msg, household = register_account(
                    account_number, homeowner_name, address, connection_type,
                    password, confirm, latitude, longitude)
                if ok:
                    log_audit_event("RESIDENT_LOGIN", household["account_number"],
                                    f"Resident {household['homeowner_name']} registered and signed in")
                    _signed_in(
                        "user", household_id=household["household_id"], household=household)
                else:
                    st.error(msg)

    # ---- Seeded accounts ---------------------------------------------------
    with panel("accounts", "Demo accounts", "Sign in with a seeded account", size="s",
               hint="All listed accounts use the shared temporary demo password provided by the operator. "
                    "Administrator credentials are in .streamlit/secrets.toml."):
        feed([(r["account_number"], f"{r['homeowner_name']} · {r['address']}")
              for r in fetch_demo_accounts()])
