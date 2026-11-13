"""Admin: audit trail and disaster / DRRM incident registry."""
from datetime import date
import sys
from pathlib import Path

import streamlit as st

# Ensure the project root is importable when this page is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from importlib import import_module

insert_disaster_incident = import_module("functions").insert_disaster_incident
from kit import empty, panel, show_toasts, stat, strip, toast
from theme import apply_theme, page_header
from ui import load_audit_logs, load_disaster_incidents, refresh_data

apply_theme()
page_header("shield", "Admin", "Immutable audit trail and disaster / DRRM incident registry.")
show_toasts()

logs = load_audit_logs()
dis = load_disaster_incidents()

with strip():
    # ---- Audit trail ---------------------------------------------------------
    with panel("audit", "Audit trail", f"{len(logs):,} events, most recent first", size="l",
               hint="Every administrative write (household added, reading recorded, incident logged) is timestamped here."):
        if logs.empty:
            empty("shield", "No audit events yet", "Administrative actions will be recorded here.")
        else:
            c1, c2 = st.columns([1, 3])
            action_filter = c1.selectbox("Action", ["All"] + sorted(logs["Action"].unique()))
            query = c2.text_input("Search", placeholder="Target or details (e.g. ACC-8001)")
            view = logs
            if action_filter != "All":
                view = view[view["Action"] == action_filter]
            if query.strip():
                q = query.strip()
                view = view[view["Target"].astype(str).str.contains(q, case=False, regex=False)
                            | view["Details"].astype(str).str.contains(q, case=False, regex=False)]
            m = st.columns(2)
            with m[0]:
                stat("Events shown", f"{len(view):,}")
            with m[1]:
                stat("Total events", f"{len(logs):,}")
            st.dataframe(view, hide_index=True, width="stretch", height=300)

    # ---- Disaster registry ---------------------------------------------------------
    with panel("disasters", "Disaster registry", f"{len(dis):,} incidents", size="l",
               hint="Cross-domain incidents used by the DRRM correlation chart. Severity drives the alert colour on the GIS map."):
        if dis.empty:
            empty("warn", "No incidents logged", "Use the Log incident panel to add one.")
        else:
            c1, c2 = st.columns(2)
            sev = c1.selectbox("Severity", ["All", "High", "Medium", "Low"])
            brgy = c2.selectbox("Barangay", ["All"] + sorted(dis["Barangay"].unique()))
            view = dis
            if sev != "All":
                view = view[view["Severity"] == sev]
            if brgy != "All":
                view = view[view["Barangay"] == brgy]
            m = st.columns(3)
            with m[0]:
                stat("Shown", f"{len(view):,}")
            with m[1]:
                stat("Total", f"{len(dis):,}")
            with m[2]:
                stat("High severity", f"{int((view['Severity'] == 'High').sum()):,}", alert=True)
            st.dataframe(view, hide_index=True, width="stretch", height=300)

    # ---- Log incident ----------------------------------------------------------------
    with panel("log", "Log incident", "Weather or grid event", size="s",
               hint="It is immediately available to the DRRM analysis and appears in the resident portal's advisory feed."):
        n = st.session_state.get("dis_form_n", 0)
        with st.form(f"add_disaster_{n}", border=False):
            barangay = st.text_input("Barangay", placeholder="Baluarte, Santiago City",
                                     help="Used for the DRRM correlation join on household address")
            itype = st.text_input("Incident type", placeholder="Typhoon / Flooding / Transformer fault")
            severity = st.segmented_control("Severity", ["High", "Medium", "Low"], default="High",
                                            key=f"adm_sev_{n}") or "High"
            date_rep = st.date_input("Date reported", value=date.today())
            submitted = st.form_submit_button("Log incident", type="primary", width="stretch")
        if submitted:
            ok, msg = insert_disaster_incident(barangay, itype, severity, date_rep.isoformat())
            if ok:
                refresh_data()
                toast(msg, "success")
                st.session_state["dis_form_n"] = n + 1
                st.rerun()
            else:
                st.error(msg)
