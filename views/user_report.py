"""Resident outage / hazard reporting — writes to disaster_incidents."""
from datetime import date

import streamlit as st

from functions import fetch_disaster_incidents, insert_disaster_incident
from kit import empty, feed, panel, show_toasts, strip, toast
from theme import apply_theme, page_header
from ui import refresh_data

apply_theme()

if st.session_state.get("role") != "user":
    st.error("Please sign in as a resident to view this page.")
    st.stop()

household = st.session_state["household"]
page_header("warn", "Report an Outage", f"Report electrical hazards in {household['address']}")
show_toasts()

barangay = household["address"].split(",")[0].strip()
ISSUE_TYPES = [
    "Transformer spark / explosion",
    "Total power outage / blackout",
    "Downed power line / cable hazard",
    "Severe weather / storm grid damage",
    "Meter tampering / suspected illegal tap",
    "Other (describe below)",
]

nearby = [d for d in fetch_disaster_incidents(limit=50)
          if barangay.lower().replace("brgy.", "").strip() in d["barangay"].lower()]

with strip():
    with panel("report", "Report an issue", f"Barangay {barangay}", size="m",
               hint="Your report goes to the grid operations team and appears on the DRRM dashboard. "
                    "The barangay is filled in from your registered address."):
        with st.form("outage_report_form"):
            incident = st.selectbox("Issue type", ISSUE_TYPES)
            severity = st.segmented_control("Severity", ["High", "Medium", "Low"],
                                            default="High", key="report_sev") or "High"
            details = st.text_area("Details / landmark",
                                   placeholder="Describe what you're seeing: where, when, and any visible damage.")
            date_obs = st.date_input("Date observed", value=date.today())
            submitted = st.form_submit_button("Submit report", type="primary",
                                              icon=":material/send:", width="stretch")
        if submitted:
            if not details.strip():
                st.error("Please describe the issue before submitting.")
            else:
                full_type = (f"{incident} (Reported by {household['homeowner_name']}: {details.strip()})")
                ok, msg = insert_disaster_incident(barangay, full_type, severity, date_obs.isoformat())
                if ok:
                    refresh_data()
                    toast(f"Report submitted to grid operations. Barangay: {barangay}", "success")
                    st.rerun()
                else:
                    st.error(msg)

    with panel("nearby", "In your barangay", f"{len(nearby)} recorded", size="m"):
        if nearby:
            feed([(d["incident_type"][:90], f"{d['date_reported']} · {d['severity_level']}",
                   "warn" if d["severity_level"] in ("High", "Medium") else "")
                  for d in nearby[:12]])
        else:
            empty("bolt", "All quiet", "No incidents recorded in your barangay.")
