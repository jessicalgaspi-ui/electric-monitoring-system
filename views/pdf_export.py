"""One-click consolidated PDF executive report.

Bundles: summary statistics, IQR anomalies, Welch T-test, OLS forecast,
disaster incident register, audit trail (last 10), and every chart from
analytics.CHART_REGISTRY as embedded PNG images.

Requires: pip install reportlab
"""

import os
from datetime import datetime
from io import BytesIO

import streamlit as st

from kit import empty, feed, panel, show_toasts, strip
from theme import apply_theme, page_header

# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _generate_pdf() -> str | None:
    """Build the PDF, save it to data/reports/, and return its path."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (HRFlowable, Image as RLImage, Paragraph,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)

    from analytics import (CHART_REGISTRY, detect_consumption_anomalies,
                           fig_to_png_bytes, forecast_next_month_consumption,
                           get_summary_statistics,
                           run_consumption_hypothesis_test)
    from database import BASE_DIR
    from functions import fetch_audit_logs, fetch_disaster_incidents

    stats = get_summary_statistics()
    if not stats:
        return None

    anomalies, threshold = detect_consumption_anomalies()
    hypo = run_consumption_hypothesis_test()
    forecast = forecast_next_month_consumption()
    disasters = fetch_disaster_incidents(limit=20)
    audit = fetch_audit_logs(limit=10)

    out_dir = os.path.join(BASE_DIR, "data", "reports")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"Smart_Grid_Report_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    path = os.path.join(out_dir, filename)

    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    # --- Styles -----------------------------------------------------------
    sheet = getSampleStyleSheet()
    NAVY = colors.HexColor("#023047")
    TEAL = colors.HexColor("#219ebc")
    ORANGE = colors.HexColor("#fb8500")
    GRAY = colors.HexColor("#4a5568")

    title_style = ParagraphStyle(
        "DocTitle", parent=sheet["Heading1"],
        fontName="Helvetica-Bold", fontSize=15, textColor=NAVY,
        alignment=1, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle", parent=sheet["Normal"],
        fontName="Helvetica", fontSize=9, textColor=GRAY,
        alignment=1, spaceAfter=10,
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=sheet["Heading2"],
        fontName="Helvetica-Bold", fontSize=11, textColor=TEAL,
        spaceBefore=10, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", parent=sheet["Normal"],
        fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#2d3748"),
        leading=12, spaceAfter=4,
    )
    caption_style = ParagraphStyle(
        "ChartCaption", parent=sheet["Normal"],
        fontName="Helvetica-Oblique", fontSize=8.5, textColor=NAVY,
        spaceBefore=4, spaceAfter=2,
    )
    cell = ParagraphStyle(
        "Cell", parent=sheet["Normal"],
        fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#2d3748"),
        leading=10,
    )
    cell_bold = ParagraphStyle(
        "CellBold", parent=sheet["Normal"],
        fontName="Helvetica-Bold", fontSize=8, textColor=NAVY, leading=10,
    )
    head_cell = ParagraphStyle(
        "HeadCell", parent=sheet["Normal"],
        fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, leading=10,
    )

    story = []

    # --- Header -----------------------------------------------------------
    story.append(
        Paragraph("SMART-GRID INTELLIGENCE & UTILITY EXECUTIVE REPORT", title_style))
    story.append(Paragraph(
        f"Echague & Santiago City Telemetry Network — Generated "
        f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        subtitle_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1.2,
                 color=NAVY, spaceAfter=8))

    # --- Section 1: Executive Summary -------------------------------------
    story.append(Paragraph("1. Executive Summary", heading_style))

    kpi_data = [
        [Paragraph(h, head_cell) for h in
         ("Metric", "Value", "Interpretation")],
        [Paragraph("Registered households", cell_bold),
         Paragraph(f"{stats['total_households']:,}", cell),
         Paragraph("Municipal nodes in the sampling frame", cell)],
        [Paragraph("Meter readings", cell_bold),
         Paragraph(f"{stats['total_readings']:,}", cell),
         Paragraph("Longitudinal billing records processed", cell)],
        [Paragraph("Cumulative load", cell_bold),
         Paragraph(f"{stats['total_consumption']:,.2f} kWh", cell),
         Paragraph("Total energy volume ingested", cell)],
        [Paragraph("Mean consumption", cell_bold),
         Paragraph(f"{stats['mean_consumption']:,.2f} kWh", cell),
         Paragraph("Baseline per-reading benchmark", cell)],
        [Paragraph("Median / σ", cell_bold),
         Paragraph(
             f"{stats['median_consumption']:,.2f} / {stats['stdev_consumption']:,.2f}", cell),
         Paragraph("Central tendency and spread", cell)],
        [Paragraph("Q1 / Q3 / IQR", cell_bold),
         Paragraph(
             f"{stats['q1']:,.2f} / {stats['q3']:,.2f} / {stats['iqr']:,.2f}", cell),
         Paragraph("Non-parametric distribution summary", cell)],
        [Paragraph("Skewness", cell_bold),
         Paragraph(f"{stats['skewness']:+.3f}", cell),
         Paragraph("Distribution asymmetry", cell)],
        [Paragraph("Total billed (flat rate)", cell_bold),
         Paragraph(f"₱{stats['total_cost']:,.2f}", cell),
         Paragraph("Estimated revenue from stored rate", cell)],
    ]
    t = Table(kpi_data, colWidths=[130, 110, 300])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f7fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    # --- Section 2: Statistical Findings ----------------------------------
    story.append(Paragraph("2. Statistical Findings", heading_style))

    findings = []
    if hypo:
        verdict = "statistically significant" if hypo["significant"] else "not significant"
        findings.append(
            f"<b>Welch's T-Test (Residential vs. Commercial):</b> "
            f"T = {hypo['t_statistic']:.4f}, p = {hypo['p_value']:.5f}, "
            f"N₁ = {hypo['n_residential']}, N₂ = {hypo['n_commercial']}. "
            f"Result is <b>{verdict}</b>. Residential mean "
            f"{hypo['mean_residential']:,.2f} kWh vs. Commercial mean "
            f"{hypo['mean_commercial']:,.2f} kWh."
        )
    else:
        findings.append(
            "<b>Welch's T-Test:</b> Insufficient data (need ≥2 readings per type).")

    if forecast:
        findings.append(
            f"<b>OLS Linear Regression Forecast:</b> Last observed period "
            f"{forecast['last_period']} at {forecast['last_consumption']:,.2f} kWh. "
            f"Slope = {forecast['slope']:+.2f} kWh/period, "
            f"R² = {forecast['r_squared']:.3f}, p = {forecast['p_value']:.4f}. "
            f"Next-period projection: <b>{forecast['predicted_load']:,.2f} kWh</b> "
            f"({forecast['trend']})."
        )
    else:
        findings.append(
            "<b>OLS Forecast:</b> Insufficient data (need ≥2 billing periods).")

    findings.append(
        f"<b>IQR Anomaly Detection:</b> Upper fence = {threshold:,.2f} kWh. "
        f"<b>{len(anomalies)}</b> reading(s) exceed this threshold and are "
        f"flagged for field inspection."
    )

    for f in findings:
        story.append(Paragraph(f, body_style))
    story.append(Spacer(1, 6))

    # --- Section 3: Disaster Incident Register ----------------------------
    story.append(
        Paragraph("3. Disaster & Grid Resilience Register", heading_style))
    if disasters:
        dis_data = [[Paragraph(h, head_cell) for h in
                    ("Date", "Barangay", "Incident", "Severity")]]
        for d in disasters:
            dis_data.append([
                Paragraph(d["date_reported"], cell),
                Paragraph(d["barangay"], cell_bold),
                Paragraph(d["incident_type"], cell),
                Paragraph(
                    f"<font color='red'><b>{d['severity_level']}</b></font>", cell),
            ])
        t = Table(dis_data, colWidths=[80, 170, 200, 90])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f7fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No disaster incidents on record.", body_style))
    story.append(Spacer(1, 6))

    # --- Section 4: Audit Trail -------------------------------------------
    story.append(Paragraph("4. Audit Trail (Last 10 Actions)", heading_style))
    if audit:
        audit_data = [[Paragraph(h, head_cell) for h in
                       ("Timestamp", "Action", "Target", "Details")]]
        for a in audit:
            audit_data.append([
                Paragraph(str(a["timestamp"]), cell),
                Paragraph(str(a["action"]), cell_bold),
                Paragraph(str(a["target"] or "—"), cell),
                Paragraph(str(a["details"] or "—"), cell),
            ])
        t = Table(audit_data, colWidths=[90, 90, 80, 280])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#fef8f0")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No audit events recorded.", body_style))
    story.append(Spacer(1, 6))

    # --- Section 5: Charts ------------------------------------------------
    story.append(Paragraph("5. Analytical Visualizations", heading_style))

    charts_rendered = 0
    for caption, builder, *_ in CHART_REGISTRY:
        fig = builder()
        if fig is None:
            continue
        try:
            png_bytes = fig_to_png_bytes(fig, dpi=140)
        finally:
            fig.clear()

        story.append(
            Paragraph(f"Figure {charts_rendered + 1}: {caption}", caption_style))
        story.append(RLImage(BytesIO(png_bytes), width=470, height=290))
        story.append(Spacer(1, 6))
        charts_rendered += 1

    if charts_rendered == 0:
        story.append(Paragraph(
            "<i>No chart data available yet — record some meter readings first.</i>",
            body_style,
        ))

    # --- Footer -----------------------------------------------------------
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#cbd5e0"), spaceAfter=4))
    story.append(Paragraph(
        f"<font color='#718096'>Generated by the Smart-Grid Intelligence "
        f"Platform — {datetime.now():%Y-%m-%d %H:%M:%S}</font>",
        body_style,
    ))

    doc.build(story)
    return path


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
apply_theme()
page_header("doc", "PDF Report", "Generate a consolidated executive PDF with all findings and charts.")
show_toasts()

with strip():
    with panel("contents", "What's inside", "Everything in one document", size="m",
               hint="Files are also saved to data/reports/."):
        feed([("Executive KPI table", "10 headline metrics"),
              ("Statistical findings", "Welch T-test, OLS forecast, IQR anomaly count"),
              ("Disaster register", "Latest incidents with severity"),
              ("Audit trail", "Last 10 administrative actions"),
              ("Charts", "Every chart from the Analytics gallery")])

    with panel("generate", "Generate", "Build and download", size="m"):
        generate = st.button("Generate PDF", type="primary", icon=":material/picture_as_pdf:", width="stretch")
        if generate:
            with st.spinner("Building PDF…"):
                try:
                    path = _generate_pdf()
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")
                    path = None
            if path and os.path.exists(path):
                with open(path, "rb") as f:
                    pdf_bytes = f.read()
                st.success(f"PDF built ({len(pdf_bytes) / 1024:.1f} KB)")
                st.download_button("Download PDF", data=pdf_bytes, file_name=os.path.basename(path),
                                   mime="application/pdf", icon=":material/download:", width="stretch")
                st.caption(f"Also saved to `{path}`")
            elif path is None:
                st.warning("No data available yet. Record some meter readings first, then try again.")
        else:
            empty("doc", "Ready when you are", "Press Generate PDF to build the report.")
