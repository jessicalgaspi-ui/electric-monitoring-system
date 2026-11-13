"""Shared Altair theme + builders used by analytics_page.py and user_readings.py."""
import altair as alt
import pandas as pd

from ui import load_monthly, load_connection_totals, load_readings

TXT = "#eaf6fc"
MUT = "rgba(234,246,252,.62)"
GRID = "rgba(142,202,230,.14)"
TEAL = "#219ebc"
SKY = "#8ecae6"
AMBER = "#ffb703"
ORANGE = "#fb8500"


def style(chart: alt.Chart) -> alt.Chart:
    return (chart
            .configure_view(stroke=None, fill="transparent")
            .configure_axis(labelColor=MUT, titleColor=MUT, gridColor=GRID,
                            domainColor="rgba(142,202,230,.3)",
                            labelFont="Inter", titleFont="Inter", labelFontSize=11)
            .configure_legend(labelColor=TXT, titleColor=MUT, orient="top",
                              labelFont="Inter", titleFont="Inter")
            .configure_title(color=TXT, font="Space Grotesk", fontSize=14, anchor="start")
            .properties(background="transparent"))


def monthly_trend(height=None):
    df = load_monthly()
    if df.empty:
        return None, df
    chart = alt.Chart(df).mark_area(
        line={"color": TEAL, "strokeWidth": 2.5},
        color=alt.Gradient(
            gradient="linear",
            stops=[alt.GradientStop(color="rgba(33,158,188,.45)", offset=0),
                   alt.GradientStop(color="rgba(33,158,188,0)", offset=1)],
            x1=1, x2=1, y1=1, y2=0),
        interpolate="monotone",
    ).encode(
        x=alt.X("Period:O", title="Period", axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("Usage (kWh):Q", title="kWh"),
        tooltip=["Period:O", alt.Tooltip("Usage (kWh):Q", format=",.1f")],
    ).properties(height=height or 330)
    return style(chart), df


def usage_by_type(height=None):
    df = load_connection_totals()
    if df.empty:
        return None, df
    chart = alt.Chart(df).mark_bar(cornerRadiusEnd=6, height=26).encode(
        y=alt.Y("Type:N", title=None, sort="-x"),
        x=alt.X("Usage (kWh):Q", title="kWh"),
        color=alt.Color("Type:N",
                        scale=alt.Scale(domain=["Residential", "Commercial"],
                                        range=[TEAL, SKY]),
                        legend=None),
        tooltip=["Type:N", alt.Tooltip("Usage (kWh):Q", format=",.1f"),
                 alt.Tooltip("Cost (₱):Q", title="Revenue (₱)", format=",.2f")],
    ).properties(height=height or 330)
    return style(chart), df


def usage_vs_sector(my_df, sector_avg, height=None):
    if my_df.empty:
        return None
    chart_df = pd.DataFrame({
        "Period": my_df["Period"].tolist() * 2,
        "Usage": my_df["Usage (kWh)"].tolist() + [sector_avg] * len(my_df),
        "Series": ["Your usage"] * len(my_df) + ["Sector average"] * len(my_df),
    })
    chart = alt.Chart(chart_df).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("Period:O", title="Period", axis=alt.Axis(labelAngle=-30)),
        xOffset="Series:N",
        y=alt.Y("Usage:Q", title="kWh"),
        color=alt.Color("Series:N",
                        scale=alt.Scale(domain=["Your usage", "Sector average"],
                                        range=[TEAL, "rgba(255,255,255,.25)"]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=["Period:O", "Series:N",
                 alt.Tooltip("Usage:Q", format=",.1f")],
    ).properties(height=height or 320)
    return style(chart)


def top_consumers(height=None):
    df = load_readings()
    if df.empty:
        return None, df
    agg = (df.groupby(["Account", "Homeowner"], as_index=False)
             .agg(**{"Usage (kWh)": ("Usage (kWh)", "sum"),
                     "Cost (₱)":   ("Cost (₱)", "sum")})
             .sort_values("Usage (kWh)", ascending=False).head(10))
    chart = alt.Chart(agg).mark_bar(cornerRadiusEnd=6, height=22).encode(
        y=alt.Y("Homeowner:N", sort="-x", title=None),
        x=alt.X("Usage (kWh):Q", title="kWh"),
        color=alt.value(TEAL),
        tooltip=["Account:N", "Homeowner:N",
                 alt.Tooltip("Usage (kWh):Q", format=",.1f"),
                 alt.Tooltip("Cost (₱):Q", title="Revenue (₱)", format=",.2f")],
    ).properties(height=height or 400)
    return style(chart), agg


def histogram_usage(height=None):
    df = load_readings()
    if df.empty:
        return None, df
    chart = alt.Chart(df).mark_bar(cornerRadiusEnd=3).encode(
        x=alt.X("Usage (kWh):Q", bin=alt.Bin(maxbins=20), title="kWh"),
        y=alt.Y("count():Q", title="Readings"),
        color=alt.value(TEAL),
        tooltip=[alt.Tooltip("count():Q")],
    ).properties(height=height or 360)
    return style(chart), df


def scatter_usage_cost(height=None):
    df = load_readings()
    if df.empty:
        return None, df
    chart = alt.Chart(df).mark_circle(size=80, opacity=.7).encode(
        x=alt.X("Usage (kWh):Q", title="kWh"),
        y=alt.Y("Cost (₱):Q", title="Revenue (₱)"),
        color=alt.Color("Type:N", scale=alt.Scale(
            domain=["Residential", "Commercial"], range=[TEAL, AMBER]), title=None),
        tooltip=["Account:N", "Period:O",
                 alt.Tooltip("Usage (kWh):Q", format=",.1f"),
                 alt.Tooltip("Cost (₱):Q", title="Revenue (₱)", format=",.2f")],
    ).interactive().properties(height=height or 400)
    return style(chart), df


CHARTS = {
    "Top consumers":   (top_consumers,   "Top 10 households by total usage",  "top_consumers.csv"),
    "Usage histogram": (histogram_usage, "Distribution of per-reading usage", "usage_histogram.csv"),
    "Usage vs revenue": (scatter_usage_cost, "Per-reading scatter",             "usage_vs_cost.csv"),
}
