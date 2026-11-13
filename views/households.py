"""Households: master-detail directory with an Add dialog."""
import altair as alt
import streamlit as st

from functions import get_household_by_id, insert_household, update_household_coordinates
from kit import empty, panel, show_toasts, stat, strip, toast
from theme import AMBER, apply_theme, page_header, style_chart
from ui import load_households, load_readings, peso, refresh_data, suggest_next_account

apply_theme()
page_header("users", "Households", "Every registered home or business account lives here.")
show_toasts()

households = load_households()


@st.dialog("Add household")
def add_household_dialog():
    n = st.session_state.get("hh_form_n", 0)
    with st.form(f"add_household_{n}", border=False):
        a, b = st.columns(2)
        account = a.text_input("Account number", value=suggest_next_account(households),
                               help="Format: ACC- followed by at least 4 digits")
        name = b.text_input("Homeowner / business name")
        c, d = st.columns([3, 1])
        address = c.text_input("Address", placeholder="Brgy. Baluarte, Santiago City")
        ctype_new = d.selectbox("Connection type", ["Residential", "Commercial"])
        st.caption("Enter verified GPS coordinates, for example coordinates from a map pin.")
        lat_col, lon_col = st.columns(2)
        latitude = lat_col.text_input("Latitude", placeholder="e.g. 16.700000")
        longitude = lon_col.text_input("Longitude", placeholder="e.g. 121.670000")
        submitted = st.form_submit_button("Save household", type="primary", width="stretch")
    if submitted:
        ok, msg = insert_household(account, name, address, ctype_new,
                                   latitude=latitude, longitude=longitude)
        if ok:
            refresh_data()
            toast(msg, "success")
            st.session_state["hh_form_n"] = n + 1
            st.rerun()
        else:
            st.error(msg)


selected = None
with strip():
    # ---- Directory -----------------------------------------------------------
    with panel("directory", "Directory", f"{len(households)} accounts", size="l",
               hint="Search by account number or name, filter by type, then click a row to see its usage."):
        if st.button("Add household", icon=":material/add:", key="open_add"):
            add_household_dialog()
        if households.empty:
            empty("users", "No households yet", "Use Add household to create the first one.")
        else:
            c1, c2 = st.columns([3, 1])
            query = c1.text_input("Search", placeholder="Account number or homeowner name")
            ctype = c2.selectbox("Type", ["All", "Residential", "Commercial"])
            view = households
            if query.strip():
                q = query.strip()
                view = view[view["Account No."].str.contains(q, case=False, regex=False)
                            | view["Homeowner"].str.contains(q, case=False, regex=False)]
            if ctype != "All":
                view = view[view["Type"] == ctype]
            view = view.reset_index(drop=True)
            st.caption(f"Showing {len(view)} of {len(households)} households")
            event = st.dataframe(view.drop(columns=["ID"]), hide_index=True, width="stretch", height=330,
                                 on_select="rerun", selection_mode="single-row", key="hh_table")
            rows = event.selection.rows if event and event.selection else []
            if rows and rows[0] < len(view):
                selected = view.iloc[rows[0]]

    # ---- Detail ----------------------------------------------------------------
    with panel("usage", "Usage history", selected["Account No."] if selected is not None else "Select a household", size="l"):
        if selected is None:
            empty("users", "Pick a household", "Click a row in the directory to see its monthly usage and billing.")
        else:
            household = get_household_by_id(int(selected["ID"]))
            readings = load_readings()
            hist = readings[readings["Account"] == selected["Account No."]].sort_values("Period")
            st.markdown(f"**{selected['Homeowner']}** · {selected['Type']}")
            st.caption("Use verified GPS or map-pin coordinates. Barangay-only addresses are not exact household locations.")
            with st.form(f"household_coordinates_{int(selected['ID'])}"):
                lat_col, lon_col = st.columns(2)
                latitude = lat_col.text_input(
                    "Latitude",
                    value="" if household["latitude"] is None else f"{household['latitude']:.6f}",
                    placeholder="e.g. 16.700000",
                )
                longitude = lon_col.text_input(
                    "Longitude",
                    value="" if household["longitude"] is None else f"{household['longitude']:.6f}",
                    placeholder="e.g. 121.670000",
                )
                submitted = st.form_submit_button("Save coordinates", type="primary")
            if submitted:
                ok, message = update_household_coordinates(
                    int(selected["ID"]), latitude, longitude
                )
                if ok:
                    refresh_data()
                    toast(message, "success")
                    st.rerun()
                else:
                    st.error(message)
            if hist.empty:
                empty("meter", "No readings yet", "Record a meter reading for this household.")
            else:
                c = st.columns(3)
                with c[0]:
                    stat("Total usage", f"{hist['Usage (kWh)'].sum():,.0f}", "kWh")
                with c[1]:
                    stat("Avg / month", f"{hist['Usage (kWh)'].mean():,.0f}", "kWh")
                with c[2]:
                    stat("Total revenue", peso(hist["Cost (₱)"].sum()))
                line = (alt.Chart(hist).mark_line(color=AMBER, strokeWidth=3, interpolate="monotone",
                                                  point=alt.OverlayMarkDef(color=AMBER, size=60))
                        .encode(x=alt.X("Period:O", title=None), y=alt.Y("Usage (kWh):Q", title="kWh"),
                                tooltip=["Period", alt.Tooltip("Usage (kWh):Q", format=",.1f"),
                                         alt.Tooltip("Cost (₱):Q", title="Revenue (₱)", format=",.2f")])
                        .properties(height=220))
                st.altair_chart(style_chart(line), theme=None)
                display_hist = hist[["Period", "Previous (kWh)", "Current (kWh)", "Usage (kWh)",
                                     "Rate (₱/kWh)", "Cost (₱)", "Reading Date"]].rename(
                                         columns={"Cost (₱)": "Revenue (₱)"})
                st.dataframe(display_hist,
                             hide_index=True, width="stretch", height=170)
