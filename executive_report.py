"""Generate the Markdown executive summary from the current database."""

from datetime import datetime
from pathlib import Path

from analytics import (
    detect_consumption_anomalies,
    forecast_next_month_consumption,
    get_summary_statistics,
    perform_consumer_clustering,
    run_consumption_hypothesis_test,
)
from database import BASE_DIR
from functions import fetch_audit_logs, fetch_disaster_incidents

REPORT_PATH = Path(BASE_DIR) / "data" / "reports" / "executive_summary.md"


def _cell(value) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def compile_executive_report() -> str:
    """Write a fresh summary report and return its absolute path."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stats = get_summary_statistics()
    anomalies, threshold = detect_consumption_anomalies()
    clusters = perform_consumer_clustering() or []
    hypothesis = run_consumption_hypothesis_test()
    forecast = forecast_next_month_consumption()
    incidents = fetch_disaster_incidents(limit=20)
    audit = fetch_audit_logs(limit=10)

    lines = [
        "# Smart-Grid Executive Summary",
        "",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "## Consumption overview",
        "",
    ]
    if stats:
        lines.extend([
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Households | {stats['total_households']:,} |",
            f"| Meter readings | {stats['total_readings']:,} |",
            f"| Total consumption | {stats['total_consumption']:,.2f} kWh |",
            f"| Mean consumption | {stats['mean_consumption']:,.2f} kWh |",
            f"| Median consumption | {stats['median_consumption']:,.2f} kWh |",
            f"| Average rate | ₱{stats['avg_rate']:.2f}/kWh |",
            f"| Total billed | ₱{stats['total_cost']:,.2f} |",
            f"| IQR anomaly threshold | {threshold:,.2f} kWh |",
            f"| Flagged readings | {len(anomalies)} |",
            "",
        ])
    else:
        lines.extend(["No consumption data is available yet.", ""])

    lines.extend(["## Anomaly review", ""])
    if anomalies:
        lines.extend([
            "| Account | Homeowner | Period | Consumption |",
            "| --- | --- | --- | ---: |",
        ])
        for item in anomalies[:20]:
            lines.append(
                f"| {_cell(item['account_number'])} | {_cell(item['homeowner_name'])} "
                f"| {_cell(item['billing_period'])} "
                f"| {item['consumption_kwh']:,.1f} kWh |"
            )
        lines.append("")
    else:
        lines.extend(["No readings exceed the current IQR threshold.", ""])

    lines.extend(["## Consumer segments", ""])
    if clusters:
        lines.extend([
            "| Account | Homeowner | Segment | Average usage | Average cost |",
            "| --- | --- | --- | ---: | ---: |",
        ])
        for item in clusters:
            lines.append(
                f"| {_cell(item['account_number'])} | {_cell(item['homeowner_name'])} "
                f"| {_cell(item['cluster'])} | {item['avg_kwh']:,.1f} kWh "
                f"| ₱{item['avg_cost']:,.2f} |"
            )
        lines.append("")
    else:
        lines.extend(["No consumer segments are available.", ""])

    lines.extend(["## Statistical analysis", ""])
    if hypothesis:
        lines.extend([
            f"- Residential mean: {hypothesis['mean_residential']:,.2f} kWh.",
            f"- Commercial mean: {hypothesis['mean_commercial']:,.2f} kWh.",
            f"- Welch t-test p-value: {hypothesis['p_value']:.5g}.",
            f"- Significant at 0.05: {'yes' if hypothesis['significant'] else 'no'}.",
        ])
    else:
        lines.append("Not enough data for a connection-type comparison.")
    if forecast:
        lines.extend([
            "",
            "### Demand forecast",
            "",
            f"- Last period: {forecast['last_period']}.",
            f"- Projected next-period load: {forecast['predicted_load']:,.2f} kWh.",
            f"- Trend: {forecast['trend']}.",
        ])
    else:
        lines.extend(["", "No forecast is available yet."])

    lines.extend(["", "## Disaster and outage incidents", ""])
    if incidents:
        lines.extend([
            "| Date | Barangay | Incident | Severity |",
            "| --- | --- | --- | --- |",
        ])
        for item in incidents:
            lines.append(
                f"| {_cell(item['date_reported'])} | {_cell(item['barangay'])} "
                f"| {_cell(item['incident_type'])} | {_cell(item['severity_level'])} |"
            )
    else:
        lines.append("No incidents have been recorded.")

    lines.extend(["", "## Recent audit activity", ""])
    if audit:
        lines.extend([
            "| Timestamp | Action | Target | Details |",
            "| --- | --- | --- | --- |",
        ])
        for item in audit:
            lines.append(
                f"| {_cell(item['timestamp'])} | {_cell(item['action'])} "
                f"| {_cell(item['target'])} | {_cell(item['details'])} |"
            )
    else:
        lines.append("No audit events have been recorded.")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(REPORT_PATH)


if __name__ == "__main__":
    print(compile_executive_report())
