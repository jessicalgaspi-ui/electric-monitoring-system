"""Statistics, machine learning, and chart builders for the merged
Smart-Grid / Electricity Monitor system.

Chart functions come in two flavours:

  fig_*()   -> returns a matplotlib Figure (Streamlit) or None
  chart_*() -> saves that figure as a PNG in data/charts/ and returns True/False

Analytics provided:
  - Descriptive statistics (mean, median, quartiles, IQR, skewness)
  - Non-parametric IQR outlier detection
  - K-Means consumer clustering (k=3)
  - Welch's t-test (Residential vs Commercial)
  - OLS linear regression forecast
  - Disaster incident <-> consumption correlation
"""
import os
import statistics
from contextlib import closing
from io import BytesIO

from database import BASE_DIR, get_connection, TIER_BOUNDS

CHARTS_DIR = os.path.join(BASE_DIR, "data", "charts")
TYPE_COLORS = {"Commercial": "#27ae60", "Residential": "#e74c3c"}


def ensure_charts_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


def _query(sql, params=()):
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# Data queries
# ---------------------------------------------------------------------------
def get_summary_statistics():
    """Returns a dict of descriptive stats, or None when no data exists."""
    row = _query("""
        SELECT COUNT(DISTINCT h.household_id),
               COUNT(r.reading_id),
               SUM(r.consumption_kwh),
               AVG(r.consumption_kwh),
               MIN(r.consumption_kwh),
               MAX(r.consumption_kwh),
               SUM(r.estimated_cost),
               AVG(r.rate_per_kwh)
        FROM households h
        LEFT JOIN meter_readings r ON h.household_id = r.household_id
    """)[0]

    consumptions = sorted(r[0] for r in _query(
        "SELECT consumption_kwh FROM meter_readings "
        "WHERE consumption_kwh IS NOT NULL"))
    costs = [r[0] for r in _query(
        "SELECT estimated_cost FROM meter_readings "
        "WHERE estimated_cost IS NOT NULL")]

    if not row or row[0] == 0 or not consumptions:
        return None

    n = len(consumptions)
    mean_c = row[3]
    median_c = statistics.median(consumptions)
    variance = statistics.variance(consumptions) if n > 1 else 0.0
    stdev = statistics.stdev(consumptions) if n > 1 else 0.0

    if n >= 2:
        q1, _, q3 = statistics.quantiles(consumptions, n=4, method="inclusive")
    else:
        q1 = q3 = consumptions[0]

    # Pearson's second skewness coefficient
    skewness = 3 * (mean_c - median_c) / stdev if stdev > 0 else 0.0

    return {
        "total_households": row[0],
        "total_readings": row[1],
        "total_consumption": row[2] or 0.0,
        "mean_consumption": mean_c or 0.0,
        "median_consumption": median_c,
        "variance_consumption": variance,
        "stdev_consumption": stdev,
        "min_consumption": row[4] or 0.0,
        "max_consumption": row[5] or 0.0,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "skewness": skewness,
        "total_cost": row[6] or 0.0,
        "avg_rate": row[7] or 0.0,
        "mean_cost": statistics.mean(costs) if costs else 0.0,
    }


def get_monthly_totals():
    """[(billing_period, total_kwh, total_cost), ...] oldest first."""
    return _query("""
        SELECT billing_period, SUM(consumption_kwh), SUM(estimated_cost)
        FROM meter_readings
        GROUP BY billing_period
        ORDER BY billing_period ASC
    """)


def get_connection_totals():
    """[(connection_type, total_kwh, total_cost), ...]"""
    return _query("""
        SELECT h.connection_type, SUM(r.consumption_kwh), SUM(r.estimated_cost)
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        GROUP BY h.connection_type
        ORDER BY h.connection_type
    """)


def get_household_totals():
    """[(account_number, homeowner_name, total_kwh, total_cost), ...] highest first."""
    return _query("""
        SELECT h.account_number, h.homeowner_name,
               SUM(r.consumption_kwh) AS total_usage,
               SUM(r.estimated_cost)
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        GROUP BY h.household_id
        ORDER BY total_usage DESC
    """)


# ---------------------------------------------------------------------------
# Advanced analytics
# ---------------------------------------------------------------------------
def detect_consumption_anomalies():
    """IQR outliers: readings > Q3 + 1.5 * IQR.

    Returns (list_of_dicts, threshold_upper_fence).
    """
    rows = _query("""
        SELECT h.account_number, h.homeowner_name,
               r.billing_period, r.consumption_kwh
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        WHERE r.consumption_kwh IS NOT NULL
    """)
    if not rows:
        return [], 0.0

    values = [r["consumption_kwh"] for r in rows]
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    threshold = q3 + 1.5 * (q3 - q1)

    anomalies = [
        dict(r) for r in rows if r["consumption_kwh"] > threshold
    ]
    return anomalies, threshold


def perform_consumer_clustering():
    """K-Means (k=3) on (avg_kwh, avg_cost) per household.

    Clusters are renumbered so 0 = lowest average consumption.
    """
    import numpy as np
    from sklearn.cluster import KMeans

    rows = _query("""
        SELECT h.account_number, h.homeowner_name, h.connection_type,
               AVG(r.consumption_kwh) AS avg_kwh,
               AVG(r.estimated_cost)  AS avg_cost
        FROM households h
        JOIN meter_readings r ON h.household_id = r.household_id
        GROUP BY h.household_id
    """)
    if len(rows) < 3:
        return None

    X = np.array([[r["avg_kwh"], r["avg_cost"]] for r in rows])
    km = KMeans(n_clusters=3, random_state=42, n_init=10).fit(X)

    # Renumber clusters so they read low → high
    order = np.argsort([c[0] for c in km.cluster_centers_])
    remap = {int(old): new for new, old in enumerate(order)}
    nice = {
        0: "Eco-Consumers (Low Load)",
        1: "Moderate Residential",
        2: "Heavy / Peak Load",
    }

    return [
        {
            "account_number": r["account_number"],
            "homeowner_name": r["homeowner_name"],
            "connection_type": r["connection_type"],
            "avg_kwh": r["avg_kwh"],
            "avg_cost": r["avg_cost"],
            "cluster": f"Cluster {remap[int(km.labels_[i])]}: "
            f"{nice[remap[int(km.labels_[i])]]}",
        }
        for i, r in enumerate(rows)
    ]


def run_consumption_hypothesis_test():
    """Welch's t-test: Residential vs Commercial consumption."""
    from scipy import stats as sp_stats

    rows = _query("""
        SELECT h.connection_type, r.consumption_kwh
        FROM meter_readings r
        JOIN households h ON r.household_id = h.household_id
        WHERE r.consumption_kwh IS NOT NULL
    """)
    res = [r["consumption_kwh"] for r in rows
           if r["connection_type"] == "Residential"]
    com = [r["consumption_kwh"] for r in rows
           if r["connection_type"] == "Commercial"]

    if len(res) < 2 or len(com) < 2:
        return None

    t, p = sp_stats.ttest_ind(res, com, equal_var=False)
    return {
        "t_statistic": float(t),
        "p_value": float(p),
        "significant": bool(p < 0.05),
        "mean_residential": statistics.mean(res),
        "mean_commercial": statistics.mean(com),
        "n_residential": len(res),
        "n_commercial": len(com),
    }


def forecast_next_month_consumption():
    """OLS linear regression on per-period SUM(consumption_kwh)."""
    from scipy import stats as sp_stats

    rows = _query("""
        SELECT billing_period, SUM(consumption_kwh) AS total_kwh
        FROM meter_readings
        GROUP BY billing_period
        ORDER BY billing_period ASC
    """)
    if len(rows) < 2:
        return None

    x = range(len(rows))
    y = [r["total_kwh"] for r in rows]
    slope, intercept, r_val, p_val, _ = sp_stats.linregress(x, y)
    predicted = float(slope * len(rows) + intercept)

    if slope > 0:
        trend = "Increasing"
    elif slope < 0:
        trend = "Decreasing"
    else:
        trend = "Flat"

    return {
        "historical_periods": len(rows),
        "last_period": rows[-1]["billing_period"],
        "last_consumption": float(rows[-1]["total_kwh"]),
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_val ** 2),
        "p_value": float(p_val),
        "predicted_load": max(0.0, predicted),
        "trend": trend,
    }


def correlate_disasters_with_anomalies():
    """Join disaster_incidents with households by barangay substring match."""
    return _query("""
        SELECT d.barangay, d.incident_type, d.severity_level, d.date_reported,
               h.account_number, h.homeowner_name, h.address,
               m.billing_period, m.consumption_kwh
        FROM disaster_incidents d
        JOIN households h
          ON h.address LIKE '%' || d.barangay || '%'
        JOIN meter_readings m
          ON m.household_id = h.household_id
        ORDER BY d.date_reported DESC
    """)


# ---------------------------------------------------------------------------
# Figure builders — return a Figure object (never touches pyplot state)
# ---------------------------------------------------------------------------
def _new_figure(w, h):
    from matplotlib.figure import Figure

    fig = Figure(figsize=(w, h))
    return fig, fig.subplots()


def fig_monthly_trend():
    rows = get_monthly_totals()
    if not rows:
        return None
    fig, ax = _new_figure(8, 5)
    ax.plot([r[0] for r in rows], [r[1] for r in rows],
            marker="o", color="#2980b9", linewidth=2.5)
    ax.set_title("System-Wide Monthly Consumption Trend", fontweight="bold")
    ax.set_xlabel("Billing Period")
    ax.set_ylabel("Total Consumption (kWh)")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    return fig


def fig_connection_comparison():
    rows = get_connection_totals()
    if not rows:
        return None
    fig, ax = _new_figure(6, 5)
    bars = ax.bar([r[0] for r in rows], [r[1] for r in rows],
                  color=[TYPE_COLORS.get(r[0], "#7f8c8d") for r in rows],
                  width=0.4)
    ax.set_title("Consumption by Connection Type", fontweight="bold")
    ax.set_xlabel("Connection Type")
    ax.set_ylabel("Total kWh")
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    ax.margins(y=0.1)
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{b.get_height():,.1f}", ha="center", va="bottom")
    fig.tight_layout()
    return fig


def fig_consumption_cost_scatter():
    rows = _query("SELECT consumption_kwh, estimated_cost FROM meter_readings")
    if not rows:
        return None
    fig, ax = _new_figure(7, 5)
    ax.scatter([r[0] for r in rows], [r[1] for r in rows],
               color="#8e44ad", alpha=0.7, edgecolors="k", s=70)
    ax.set_title("Consumption (kWh) vs. Estimated Cost (₱)", fontweight="bold")
    ax.set_xlabel("Consumption (kWh)")
    ax.set_ylabel("Cost (₱)")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    return fig


def fig_consumption_distribution():
    rows = [r[0] for r in _query(
        "SELECT consumption_kwh FROM meter_readings "
        "WHERE consumption_kwh IS NOT NULL")]
    if not rows:
        return None
    fig, ax = _new_figure(7, 5)
    ax.hist(rows, bins=8, color="#e67e22", edgecolor="black", alpha=0.8)
    ax.set_title("Distribution of Household Monthly Consumption",
                 fontweight="bold")
    ax.set_xlabel("Consumption (kWh)")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    fig.tight_layout()
    return fig


def fig_household_rankings():
    rows = list(reversed(get_household_totals()))
    if not rows:
        return None
    fig, ax = _new_figure(8, 5)
    ax.barh([r[0] for r in rows], [r[2] for r in rows], color="#34495e")
    ax.set_title("Total Consumption Ranking per Account", fontweight="bold")
    ax.set_xlabel("Total Consumption (kWh)")
    ax.set_ylabel("Account Number")
    ax.grid(axis="x", linestyle="--", alpha=0.6)
    fig.tight_layout()
    return fig


def fig_iqr_outliers():
    rows = _query("""
        SELECT consumption_kwh FROM meter_readings
        WHERE consumption_kwh IS NOT NULL
    """)
    if not rows:
        return None

    values = [r[0] for r in rows]
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr

    fig, ax = _new_figure(8, 5)
    xs = list(range(len(values)))
    colors = ["#e74c3c" if (v < lower or v > upper) else "#3498db"
              for v in values]
    ax.scatter(xs, values, c=colors, s=60, alpha=0.75, edgecolors="k")
    ax.axhline(upper, color="#e74c3c", linestyle="--",
               label=f"Upper fence = {upper:,.0f} kWh")
    ax.axhline(lower, color="#f39c12", linestyle="--",
               label=f"Lower fence = {lower:,.0f} kWh")
    ax.axhline(q1, color="#95a5a6", linestyle=":", alpha=0.6)
    ax.axhline(q3, color="#95a5a6", linestyle=":", alpha=0.6)
    ax.set_title("IQR Outlier Detection", fontweight="bold")
    ax.set_xlabel("Reading index")
    ax.set_ylabel("Consumption (kWh)")
    ax.legend(fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_kmeans_clusters():
    result = perform_consumer_clustering()
    if not result:
        return None
    fig, ax = _new_figure(8, 5)
    palette = {"Eco": "#27ae60", "Moderate": "#f39c12", "Heavy": "#e74c3c"}
    for r in result:
        color = next((v for k, v in palette.items() if k in r["cluster"]),
                     "#7f8c8d")
        ax.scatter(r["avg_kwh"], r["avg_cost"], color=color, s=85,
                   edgecolors="k", alpha=0.85)
    ax.set_title("K-Means Consumer Segmentation (k=3)", fontweight="bold")
    ax.set_xlabel("Average Consumption (kWh)")
    ax.set_ylabel("Average Cost (₱)")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_regression_forecast():
    fc = forecast_next_month_consumption()
    if fc is None:
        return None

    rows = _query("""
        SELECT billing_period, SUM(consumption_kwh)
        FROM meter_readings
        GROUP BY billing_period
        ORDER BY billing_period ASC
    """)
    periods = [r[0] for r in rows]
    y = [r[1] for r in rows]
    trend = [
        fc["slope"] * index + fc["intercept"]
        for index in range(len(rows))
    ]

    fig, ax = _new_figure(8, 5)
    ax.plot(periods, y, "o-", color="#2980b9", label="Actual")
    ax.plot(periods, trend, "--", color="#e67e22",
            label=f"OLS (slope={fc['slope']:+.1f} kWh/period)")
    ax.scatter([f"Next ({fc['last_period'][:4]})"], [fc["predicted_load"]],
               color="#e74c3c", s=220, marker="*", zorder=5,
               label=f"Forecast: {fc['predicted_load']:,.0f} kWh")
    ax.set_title("Time-Series Linear Regression Forecast", fontweight="bold")
    ax.set_xlabel("Billing Period")
    ax.set_ylabel("Total Consumption (kWh)")
    ax.legend(fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout()
    return fig


def fig_tier_distribution():
    rows = _query("""
        SELECT consumption_kwh FROM meter_readings
        WHERE consumption_kwh IS NOT NULL
    """)
    if not rows:
        return None

    b1, b2 = TIER_BOUNDS
    lifeline = sum(1 for r in rows if r[0] <= b1)
    standard = sum(1 for r in rows if b1 < r[0] <= b2)
    peak = sum(1 for r in rows if r[0] > b2)

    fig, ax = _new_figure(7, 5)
    labels = [
        f"Lifeline\n(≤{b1:g} kWh)",
        f"Standard\n({b1:g}–{b2:g} kWh)",
        f"Peak\n(>{b2:g} kWh)",
    ]
    bars = ax.bar(labels, [lifeline, standard, peak],
                  color=["#38a169", "#d69e2e", "#e53e3e"],
                  edgecolor="black", width=0.55)
    for b, v in zip(bars, [lifeline, standard, peak]):
        ax.text(b.get_x() + b.get_width() / 2, v, str(v),
                ha="center", va="bottom", fontweight="bold")
    ax.set_title("Tariff Tier Distribution", fontweight="bold")
    ax.set_ylabel("Number of Readings")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_disaster_correlation():
    rows = correlate_disasters_with_anomalies()
    if not rows:
        return None

    counts, seen = {}, set()
    for r in rows:
        key = (r["barangay"], r["incident_type"], r["date_reported"])
        if key not in seen:
            seen.add(key)
            counts[r["barangay"]] = counts.get(r["barangay"], 0) + 1

    fig, ax = _new_figure(8, 5)
    ax.barh(list(counts.keys()), list(counts.values()),
            color="#c0392b", edgecolor="black")
    ax.set_title("Disaster Incidents by Barangay", fontweight="bold")
    ax.set_xlabel("Number of Incidents")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Registry — used by views/analytics_page.py and views/pdf_export.py
# ---------------------------------------------------------------------------
CHART_REGISTRY = [
    ("Monthly Consumption Trend",       fig_monthly_trend,
     "monthly_consumption_trend.png"),
    ("Connection Type Comparison",      fig_connection_comparison,
     "connection_type_comparison.png"),
    ("Consumption vs. Cost",            fig_consumption_cost_scatter,
     "consumption_vs_cost_scatter.png"),
    ("Consumption Distribution",        fig_consumption_distribution,
     "consumption_histogram.png"),
    ("Household Rankings",              fig_household_rankings,
     "household_consumption_ranking.png"),
    ("IQR Outlier Detection",           fig_iqr_outliers,
     "iqr_outlier_chart.png"),
    ("K-Means Consumer Clusters",       fig_kmeans_clusters,
     "kmeans_cluster_chart.png"),
    ("Regression Demand Forecast",      fig_regression_forecast,
     "regression_forecast_chart.png"),
    ("Tariff Tier Distribution",        fig_tier_distribution,
     "tier_distribution_chart.png"),
    ("Disaster Incidents by Barangay",  fig_disaster_correlation,
     "disaster_correlation_chart.png"),
]


def fig_to_png_bytes(fig, dpi=200):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers — save charts to disk
# ---------------------------------------------------------------------------
def _save(fig, filename):
    if fig is None:
        return False
    ensure_charts_dir()
    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=300)
    fig.clear()
    return True


def _saver(fig_builder, filename):
    return lambda: _save(fig_builder(), filename)


chart_monthly_trend = _saver(fig_monthly_trend,
                             "monthly_consumption_trend.png")
chart_connection_comparison = _saver(fig_connection_comparison,
                                     "connection_type_comparison.png")
chart_consumption_cost_scatter = _saver(fig_consumption_cost_scatter,
                                        "consumption_vs_cost_scatter.png")
chart_consumption_distribution = _saver(fig_consumption_distribution,
                                        "consumption_histogram.png")
chart_household_rankings = _saver(fig_household_rankings,
                                  "household_consumption_ranking.png")


def generate_all_charts():
    """Save every chart in the registry to data/charts/. Returns True/False."""
    return all(_save(builder(), filename)
               for _, builder, filename in CHART_REGISTRY)


# ---------------------------------------------------------------------------
# CLI diagnostic report
# ---------------------------------------------------------------------------
def print_full_diagnostic_report():
    stats = get_summary_statistics()
    if not stats:
        print("\n[INFO] No analytical data available to print.")
        return False

    anomalies, threshold = detect_consumption_anomalies()
    hypo = run_consumption_hypothesis_test()
    fc = forecast_next_month_consumption()

    print("\n" + "=" * 65)
    print(" HOUSEHOLD ELECTRICITY CONSUMPTION - FULL DIAGNOSTIC REPORT ".center(65))
    print("=" * 65)
    print(f" Registered Households    : {stats['total_households']}")
    print(f" Total Meter Readings     : {stats['total_readings']}")
    print(f" Cumulative Consumption   : {stats['total_consumption']:,.2f} kWh")
    print(f" Mean / Median Usage      : {stats['mean_consumption']:,.2f} / "
          f"{stats['median_consumption']:,.2f} kWh")
    print(f" Std Dev / Variance       : {stats['stdev_consumption']:,.2f} / "
          f"{stats['variance_consumption']:,.2f}")
    print(f" Min / Max Usage          : {stats['min_consumption']:,.2f} / "
          f"{stats['max_consumption']:,.2f} kWh")
    print(f" Q1 / Q3 / IQR            : {stats['q1']:,.2f} / "
          f"{stats['q3']:,.2f} / {stats['iqr']:,.2f} kWh")
    print(f" Distribution Skewness    : {stats['skewness']:.3f}")
    print("-" * 65)
    print(f" Average Rate             : ₱{stats['avg_rate']:.2f}/kWh")
    print(f" Mean Estimated Cost      : ₱{stats['mean_cost']:,.2f}")
    print(f" Total Billed (flat rate) : ₱{stats['total_cost']:,.2f}")
    print("-" * 65)
    print(f" IQR Outlier Threshold    : {threshold:,.2f} kWh")
    print(f" Flagged Anomalies        : {len(anomalies)}")
    for a in anomalies[:5]:
        print(f"   - {a['account_number']} ({a['homeowner_name']}): "
              f"{a['consumption_kwh']:,.1f} kWh in {a['billing_period']}")
    if len(anomalies) > 5:
        print(f"   ... and {len(anomalies) - 5} more.")
    print("-" * 65)
    if hypo:
        print(" Welch T-Test (Residential vs Commercial):")
        print(f"   Residential: mean {hypo['mean_residential']:,.2f} kWh "
              f"(n={hypo['n_residential']})")
        print(f"   Commercial : mean {hypo['mean_commercial']:,.2f} kWh "
              f"(n={hypo['n_commercial']})")
        print(f"   T = {hypo['t_statistic']:.4f},  p = {hypo['p_value']:.5f} "
              f"({'Significant' if hypo['significant'] else 'Not significant'})")
    else:
        print(" Welch T-Test: insufficient data (need ≥2 readings per type).")
    print("-" * 65)
    if fc:
        print(" OLS Linear Regression Forecast:")
        print(f"   Last period ({fc['last_period']}): "
              f"{fc['last_consumption']:,.2f} kWh")
        print(f"   Slope: {fc['slope']:+.2f} kWh/period  |  "
              f"R²={fc['r_squared']:.3f}  |  p={fc['p_value']:.4f}")
        print(f"   Next-period projection: {fc['predicted_load']:,.2f} kWh  "
              f"({fc['trend']})")
    else:
        print(" OLS Forecast: insufficient data (need ≥2 billing periods).")
    print("=" * 65)
    return True
