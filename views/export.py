"""Export: one card per CSV file, plus a preview of the statistical summary."""
import pandas as pd
import streamlit as st

from kit import empty, panel, show_toasts, strip
from theme import apply_theme, page_header
from ui import load_households, load_readings, load_summary

apply_theme()
page_header("down", "Export", "Download your data as CSV files (opens correctly in Excel).")
show_toasts()


def to_csv(df):
    display_df = df.rename(columns={"Cost (₱)": "Revenue (₱)"}).copy()
    if "Statistic" in display_df.columns:
        display_df["Statistic"] = display_df["Statistic"].str.replace(
            "_cost", "_revenue", regex=False
        )
    return display_df.to_csv(index=False).encode("utf-8-sig")  # BOM keeps the peso sign intact in Excel


households = load_households()
readings = load_readings()
stats = load_summary()
summary = None
if stats is not None:
    summary = pd.DataFrame({"Statistic": list(stats.keys()), "Value": list(stats.values())})

with strip():
    with panel("files", "Files", "Each card is one CSV", size="l",
               hint="Pick what you need and press its download button."):
        c1, c2, c3 = st.columns(3)
        with c1, st.container(key="tile-export-hh"):
            st.markdown("**Households**")
            st.caption(f"{len(households)} rows · every registered account")
            st.download_button("households.csv", to_csv(households), "households.csv", "text/csv",
                               disabled=households.empty, icon=":material/download:", width="stretch")
        with c2, st.container(key="tile-export-rd"):
            st.markdown("**Meter readings**")
            st.caption(f"{len(readings)} rows · usage, rate and revenue")
            st.download_button("meter_readings.csv", to_csv(readings), "meter_readings.csv", "text/csv",
                               disabled=readings.empty, icon=":material/download:", width="stretch")
        with c3, st.container(key="tile-export-sm"):
            st.markdown("**Statistical summary**")
            if summary is None:
                st.caption("No data available yet.")
            else:
                st.caption(f"{len(summary)} statistics · mean, spread, totals")
                st.download_button("summary_statistics.csv", to_csv(summary), "summary_statistics.csv",
                                   "text/csv", icon=":material/download:", width="stretch")

    with panel("preview", "Preview", "Statistical summary", size="m"):
        if summary is None:
            empty("doc", "Nothing to preview", "Record some meter readings first.")
        else:
            st.dataframe(summary, hide_index=True, width="stretch", height=330)
