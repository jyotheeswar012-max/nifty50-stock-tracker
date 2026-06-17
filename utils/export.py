"""Data export helpers — CSV bytes and PDF bytes from a DataFrame.

All public functions are pure (no Streamlit).  Call export_buttons()
from page modules to render the download widgets.
"""
from __future__ import annotations

import io
from typing import Optional

import pandas as pd
import streamlit as st

from utils.logger import get_logger

log = get_logger(__name__)


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialise *df* to UTF-8 CSV bytes (BOM-prefixed for Excel compat)."""
    try:
        buf = io.StringIO()
        df.to_csv(buf, index=True, encoding="utf-8-sig")
        return buf.getvalue().encode("utf-8-sig")
    except Exception as exc:
        log.error("df_to_csv_bytes failed: %s", exc, exc_info=True)
        return b""


def df_to_pdf_bytes(df: pd.DataFrame, title: str = "NSE Tracker Export") -> Optional[bytes]:
    """Render *df* as a single-page PDF using ReportLab.

    Returns None if ReportLab is not installed, so callers can hide the
    PDF button gracefully rather than crashing.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
        )
    except ImportError:
        log.warning("df_to_pdf_bytes: ReportLab not installed — PDF export unavailable")
        return None

    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=landscape(A4),
            rightMargin=1 * cm, leftMargin=1 * cm,
            topMargin=1.5 * cm, bottomMargin=1 * cm,
        )
        styles = getSampleStyleSheet()
        elements = [
            Paragraph(title, styles["Title"]),
            Spacer(1, 0.4 * cm),
        ]

        # Build table data: header + rows (stringify everything)
        display_df = df.reset_index()
        header = list(display_df.columns)
        rows   = [[str(v) for v in row] for row in display_df.itertuples(index=False, name=None)]
        data   = [header] + rows

        col_w = (landscape(A4)[0] - 2 * cm) / len(header)
        tbl   = Table(data, colWidths=[col_w] * len(header), repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#6366f1")),
            ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID",        (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ("TOPPADDING",  (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(tbl)
        doc.build(elements)
        return buf.getvalue()
    except Exception as exc:
        log.error("df_to_pdf_bytes failed: %s", exc, exc_info=True)
        return None


def export_buttons(
    df: pd.DataFrame,
    filename_stem: str = "nse_export",
    title: str = "NSE Tracker Export",
    key_suffix: str = "",
) -> None:
    """Render CSV (always) and PDF (if ReportLab present) download buttons.

    Parameters
    ----------
    df            : DataFrame to export.
    filename_stem : Base filename without extension.
    title         : Title string embedded in the PDF.
    key_suffix    : Appended to Streamlit widget keys for uniqueness.
    """
    if df is None or df.empty:
        st.caption("No data to export.")
        return

    col_csv, col_pdf = st.columns([1, 1])

    # CSV is always available
    csv_bytes = df_to_csv_bytes(df)
    if csv_bytes:
        col_csv.download_button(
            label="\U0001f4c5 Download CSV",
            data=csv_bytes,
            file_name=f"{filename_stem}.csv",
            mime="text/csv",
            key=f"_export_csv_{key_suffix}",
            use_container_width=True,
        )
    else:
        col_csv.caption("CSV unavailable")

    # PDF only if ReportLab is installed
    pdf_bytes = df_to_pdf_bytes(df, title=title)
    if pdf_bytes is not None:
        col_pdf.download_button(
            label="\U0001f4c4 Download PDF",
            data=pdf_bytes,
            file_name=f"{filename_stem}.pdf",
            mime="application/pdf",
            key=f"_export_pdf_{key_suffix}",
            use_container_width=True,
        )
    else:
        col_pdf.caption("PDF export: install `reportlab` to enable")
