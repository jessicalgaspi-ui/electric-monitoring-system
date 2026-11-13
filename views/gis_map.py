"""Admin GIS map: every household as a dot, disasters as orange beacons."""
import streamlit as st

from functions import fetch_all_households_geo, fetch_disaster_incidents
from kit import empty, panel, show_toasts, stat, strip
from maps import (ORANGE, SKY, TEAL, barangay_key, base_map, coordinate_text,
                  dot, hazard, household_position, legend, popup, render)
from theme import apply_theme, page_header

apply_theme()
page_header("map", "GIS Map", "Households plotted at their stored coordinates across Echague and Santiago City.")
show_toasts()

rows = fetch_all_households_geo()
if not rows:
    with strip():
        with panel("empty", "No households", "", size="m"):
            empty("map", "Nothing to plot", "Add a household from the Households page.")
    st.stop()

with strip():
    # Filters come first in the script so the map below can use their values.
    with panel("filters", "Filters", "What to show", size="s"):
        type_filter = st.multiselect("Connection type", ["Residential", "Commercial"],
                                     default=["Residential", "Commercial"])
        status_filter = st.multiselect("Status", ["Active", "Overdue", "Inactive", "Suspended", "Disconnected"],
                                       default=["Active", "Overdue", "Inactive", "Suspended", "Disconnected"])
        show_disasters = st.toggle("Show emergency incidents", value=True)
        summary = st.container()

    mappable = []
    unmapped_count = 0
    for row in rows:
        if row["connection_type"] not in type_filter or row["status"] not in status_filter:
            continue
        position = household_position(row, rows)
        if position is None:
            unmapped_count += 1
        else:
            mappable.append((row, position))

    with panel("map", "Network map", "Click any marker for full details", size="xl",
               hint="Households without GPS are shown at an approximate position derived from mapped households in the same barangay. Emergency markers pulse at every severity and indicate an approximate barangay location."):
        st.caption("Click household markers to see all accounts at that map point. Update approximate pins with verified GPS or map-pin coordinates from the Households page.")
        if not mappable:
            empty("map", "No households match", "Adjust the filters.")
            disaster_count = 0
        else:
            m = base_map([16.78, 121.61], 11)
            map_points = []
            grouped_households = {}
            for r, position in mappable:
                pos = position[:2]
                map_points.append(pos)
                grouped_households.setdefault(pos, []).append((r, position[2]))
            for pos, group in grouped_households.items():
                color = SKY if all(r["connection_type"] == "Commercial" for r, _ in group) else TEAL
                lines = []
                for r, approximate in group:
                    suffix = " (approximate locality pin)" if approximate else ""
                    lines.append((r["account_number"],
                                  f"{r['homeowner_name']} · {r['connection_type']} · {r['status']}{suffix}"))
                    lines.append(("Address", r["address"]))
                lines.append(("Coordinates", coordinate_text(*pos)))
                label = f"{len(group)} households at this location" if len(group) > 1 else (
                    f"{group[0][0]['account_number']} — {group[0][0]['homeowner_name']}"
                )
                dot(m, pos[0], pos[1], color, 6, label,
                    popup(f"{len(group)} household(s)", lines, color, width=260))

            disaster_count = 0
            if show_disasters:
                coords = {}
                for r in rows:
                    position = household_position(r, rows)
                    if position is None:
                        continue
                    key = barangay_key(r["address"])
                    if key:
                        coords.setdefault(key, []).append(position[:2])
                for d in fetch_disaster_incidents(limit=100):
                    bkey = barangay_key(d["barangay"])
                    positions = coords.get(bkey)
                    if not positions:
                        continue
                    pos = (sum(point[0] for point in positions) / len(positions),
                           sum(point[1] for point in positions) / len(positions))
                    map_points.append(pos)
                    hazard(m, pos[0], pos[1], d["severity_level"],
                           f"{d['incident_type'][:60]} ({d['severity_level']}) — {d['barangay']}",
                           popup(d["incident_type"][:80], [("Barangay", d["barangay"]),
                                                           ("Severity", d["severity_level"]),
                                                           ("Reported", d["date_reported"]),
                                                           ("Location", "Approximate barangay position"),
                                                           ("Coordinates", coordinate_text(*pos))], "#ffb35c"))
                    disaster_count += 1
            if len(map_points) > 1:
                m.fit_bounds(map_points, padding=(24, 24), max_zoom=13)
            elif map_points:
                m.location = map_points[0]
                m.zoom_start = 13
            legend(m, [(TEAL, "Residential"), (SKY, "Commercial"),
                       (ORANGE, "Emergency (approx. barangay location)")])
            render(m, height=520)
        if unmapped_count:
            st.warning(f"{unmapped_count} household(s) have no coordinates or mapped household in their barangay, so they cannot be placed on this map yet.")

    with summary:
        stat("Households on map", f"{len(mappable):,}", alert=unmapped_count > 0)
        c = st.columns(2)
        with c[0]:
            stat("Residential", f"{sum(1 for r, _ in mappable if r['connection_type'] == 'Residential'):,}")
        with c[1]:
            stat("Commercial", f"{sum(1 for r, _ in mappable if r['connection_type'] == 'Commercial'):,}")
        stat("Emergency markers", f"{disaster_count:,}", alert=disaster_count > 0)
