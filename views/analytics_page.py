"""Analytics: Trends · Statistics · Chart gallery · PNG export, as sideways panels."""
import matplotlib.pyplot as plt
import streamlit as st

from analytics import CHART_REGISTRY, fig_to_png_bytes
from charts import CHARTS, monthly_trend, usage_by_type
from kit import empty, kv, panel, range_bar, show_toasts, stat, strip
from theme import apply_theme, page_header, style_chart
from ui import load_highest_consumer, load_summary, peso

apply_theme()
page_header("chart", "Analytics", "Understand consumption patterns, statistics and billing totals.")
show_toasts()

stats = load_summary()
if stats is None:
    with strip():
        with panel("empty", "No analytical data yet", "", size="m"):
            empty("meter", "Nothing to analyze", "Record some meter readings first.")
    st.stop()


def show_chart(builder, height=None):
    """Render an interactive chart; never let a chart problem break the page."""
    try:
        chart, data = builder(height) if height else builder()
    except Exception as exc:
        st.warning(f"This chart could not be drawn ({exc}).")
        return None
    if chart is None:
        st.info("No data for this chart yet.")
        return None
    st.altair_chart(style_chart(chart), theme=None)
    return data


top = load_highest_consumer()

with strip():
    # ---- Trends --------------------------------------------------------------
    with panel("trends", "Trends", "Month to month, and by connection type", size="l",
               hint="Hover over the charts to see exact values."):
        st.markdown("**Monthly consumption**")
        show_chart(monthly_trend, 250)
        st.markdown("**Residential vs Commercial**")
        show_chart(usage_by_type, 250)

    # ---- Statistics ----------------------------------------------------------------
    with panel("stats", "Statistics", "Plain numbers about every reading", size="m",
               hint="Typical value, how spread out readings are, and the money involved."):
        stat("Projected revenue", peso(stats["total_cost"]), hero=True,
             foot=f"{stats['total_households']:,} households · {stats['total_readings']:,} readings")
        c = st.columns(3)
        with c[0]:
            stat("Mean", f"{stats['mean_consumption']:,.1f}", "kWh")
        with c[1]:
            stat("Median", f"{stats['median_consumption']:,.1f}", "kWh")
        with c[2]:
            stat("Std. dev", f"{stats['stdev_consumption']:,.1f}")
        st.caption("Spread of readings (box = Q1 to Q3, marker = median)")
        range_bar(stats["q1"], stats["median_consumption"], stats["q3"],
                  stats["min_consumption"], stats["max_consumption"])
        kv([("Variance", f"{stats['variance_consumption']:,.2f}"), ("IQR", f"{stats['iqr']:,.2f}"),
            ("Average rate", f"{peso(stats['avg_rate'])}/kWh"), ("Mean revenue / reading", peso(stats["mean_cost"]))])
        skew = stats["skewness"]
        shape = ("right-skewed: a few high consumers pull the average up" if skew > 0.5 else
                 "left-skewed: a few very low readings pull the average down" if skew < -0.5 else
                 "fairly symmetric")
        st.caption(f"Skewness {skew:.3f} - the distribution is {shape}.")

    # ---- Top consumer --------------------------------------------------------------
    if top:
        with panel("top", "Highest consumer", top[2], size="s"):
            stat("Total usage", f"{top[4]:,.0f}", "kWh", alert=True, hero=True)
            kv([("Account", top[0]), ("Homeowner", top[1]), ("Type", top[3]), ("Total revenue", peso(top[5]))])

    # ---- Chart gallery --------------------------------------------------------------
    with panel("gallery", "Chart gallery", "Pick a chart", size="l",
               hint="Charts are interactive: hover for details; on the scatter plot scroll to zoom and drag to pan."):
        pick = st.radio("Chart", list(CHARTS), horizontal=True, label_visibility="collapsed")
        builder, description, csv_name = CHARTS[pick]
        st.caption(description)
        data = show_chart(builder, 330)
        if data is not None:
            export_data = data.rename(columns={"Cost (₱)": "Revenue (₱)"})
            st.download_button("Data (CSV)", export_data.to_csv(index=False).encode("utf-8-sig"), csv_name,
                               "text/csv", key=f"csv_{csv_name}", icon=":material/download:")

    # ---- PNG export ------------------------------------------------------------------
    with panel("png", "PNG export", "Download a chart as an image", size="m"):
        titles = [t for t, _, _ in CHART_REGISTRY]
        pick_png = st.selectbox("Chart to export", titles)
        title, builder_png, filename = CHART_REGISTRY[titles.index(pick_png)]
        fig = builder_png()
        if fig is None:
            st.info(f"No data for '{title}'.")
        else:
            try:
                fig.set_size_inches(9, 3.6)
            except Exception:
                pass
            st.pyplot(fig)
            st.download_button("Download PNG", data=fig_to_png_bytes(fig), file_name=filename,
                               mime="image/png", key=f"dl_{filename}", icon=":material/download:")
            plt.close(fig)
