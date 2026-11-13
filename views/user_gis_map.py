"""Resident GIS map — your household, neighbours, the wider grid and nearby hazards."""
import streamlit as st

from functions import fetch_all_households_geo, fetch_disaster_incidents
from kit import empty, feed, panel, show_toasts, stat, strip
from maps import (AMBER, GRAY, TEAL, barangay_key, base_map, coordinate_text,
                  dot, hazard, household_position, legend, popup, render)
from theme import apply_theme, page_header

apply_theme()

if st.session_state.get("role") != "user":
    st.error("Please sign in as a resident to view this page.")
    st.stop()

household = st.session_state["household"]


user_core = barangay_key(household["address"])
page_header("map", "My Area", household["address"])
show_toasts()

all_rows = fetch_all_households_geo()
disasters = fetch_disaster_incidents(limit=100)
my_row = next((r for r in all_rows if r["account_number"] == household["account_number"]), None)
my_position = household_position(my_row, all_rows) if my_row is not None else None
if my_position is None:
    st.warning("Your account doesn't have coordinates, and no mapped household in your barangay is available to estimate your position. "
               "Contact your grid operator to update your address.")
    st.stop()

my_lat, my_lon, my_approximate = my_position
geo = []
for row in all_rows:
    if row["account_number"] == household["account_number"]:
        continue
    position = household_position(row, all_rows)
    if position is not None:
        geo.append((row, position))
neighbours = [(r, pos) for r, pos in geo if barangay_key(r["address"]) == user_core]
remote = [(r, pos) for r, pos in geo if barangay_key(r["address"]) != user_core]
nearby = [d for d in disasters if barangay_key(d["barangay"]) == user_core]

m = base_map([my_lat, my_lon], 14)
for r, position in remote:
    lat, lon, approximate = position
    detail = "Approximate location" if approximate else coordinate_text(lat, lon)
    dot(m, lat, lon, GRAY, 4, "Other monitored household",
        popup(r["homeowner_name"], [("Address", r["address"]), ("Location", detail)], GRAY),
        fill=0.5, weight=1)
for r, position in neighbours:
    lat, lon, approximate = position
    if approximate and r["latitude"] is not None:
        detail = "Approximate locality pin (synthetic demo data)"
    elif approximate:
        detail = "Approximate barangay estimate (no GPS saved)"
    else:
        detail = coordinate_text(lat, lon)
    dot(m, lat, lon, TEAL, 7, f"{r['account_number']} — {r['homeowner_name']}",
        popup(r["homeowner_name"], [("Address", r["address"]), ("Type", r["connection_type"]),
                                    ("Status", r["status"]), ("Location", detail)], TEAL))
if my_approximate and my_row["latitude"] is not None:
    my_location = "Approximate locality pin (synthetic demo data)"
elif my_approximate:
    my_location = "Approximate barangay estimate (no GPS saved)"
else:
    my_location = coordinate_text(my_lat, my_lon)
dot(m, my_lat, my_lon, AMBER, 11, "You are here",
    popup("Your household", [("Name", household["homeowner_name"]), ("Account", household["account_number"]),
                             ("Type", household["connection_type"]), ("Status", household["status"]),
                             ("Location", my_location)], AMBER),
    weight=3, pulse=True)

# Hazards carry only a barangay, not coordinates: plot at the barangay centre
# (mean of the households we know there), one marker per incident, same spot.
centre_pts = [(my_lat, my_lon)] + [(position[0], position[1]) for _, position in neighbours]
clat = sum(p[0] for p in centre_pts) / len(centre_pts)
clon = sum(p[1] for p in centre_pts) / len(centre_pts)
for d in sorted(nearby, key=lambda x: {"High": 2, "Medium": 1}.get(x["severity_level"], 0)):
    hazard(m, clat, clon, d["severity_level"], f"{d['incident_type'][:60]} ({d['severity_level']})",
           popup(d["incident_type"][:80], [("Severity", d["severity_level"]), ("Reported", d["date_reported"]),
                                           ("Location", "Approx. barangay centre")], "#ffb35c"))
legend(m, [(AMBER, "Your household"), (TEAL, "Neighbours"), (GRAY, "Other households"),
           ("#fb8500", "Emergency (approx. barangay location)")])

with strip():
    with panel("map", "My area", "Click any marker for details", size="l",
               hint="Households without saved GPS use an approximate position based on mapped households in the same barangay. Emergency markers are also approximate."):
        st.caption("Pins without saved GPS are placed approximately using mapped households in the same barangay. Emergency pins pulse at all severity levels and are approximate because reports contain a barangay, not an exact location.")
        render(m, height=520)

    with panel("nearby", "Around you", user_core.title(), size="s"):
        c = st.columns(2)
        with c[0]:
            stat("Neighbours", len(neighbours))
        with c[1]:
            stat("Emergencies", len(nearby), alert=bool(nearby))
        stat("Other households", len(remote))
        if nearby:
            feed([(d["incident_type"][:70], f"{d['date_reported']} · {d['severity_level']}",
                   "warn" if d["severity_level"] != "Low" else "") for d in nearby[:8]])
        else:
            empty("bolt", "All clear", "No reported emergencies in your barangay.")
