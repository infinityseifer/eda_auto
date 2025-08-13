"""Narrative generation for Auto-EDA MVP.

Two modes:
- Rule-based: deterministic summaries from computed stats (default)
- LLM-assisted: a hook to call an LLM and return structured sections (wire later)
"""
from __future__ import annotations

from typing import Dict


def _fmt_pct(x: float | int, total: float | int) -> str:
    if not total:
        return "0%"
    return f"{(float(x)/float(total))*100:.1f}%"


def generate_narrative(eda: Dict) -> Dict[str, object]:
    """Create a compact, decision-oriented narrative from EDA stats.

    Parameters
    ----------
    eda : dict
        Output from `run_eda` containing `stats` and (optionally) `charts`.
    """
    st = eda.get("stats", {})
    n_rows = st.get("n_rows", 0)
    n_cols = st.get("n_cols", 0)
    missing_by_col = st.get("missing_by_col", {})
    top_missing = list(missing_by_col.items())[:5]

    num_summary = st.get("numeric_summary", [])
    top_corr = st.get("top_correlations", [])

    # Executive summary
    exec_lines = [
        f"Dataset with {n_rows:,} rows and {n_cols} columns.",
    ]
    if top_missing:
        miss_cols = ", ".join([f"{k} ({v})" for k, v in top_missing])
        exec_lines.append(f"Missing values concentrated in: {miss_cols}.")
    if top_corr:
        c0 = top_corr[0]
        exec_lines.append(
            f"Strongest numeric relationship: {c0['col_x']} ~ {c0['col_y']} (|r|={c0['abs_r']})."
        )

    # Data overview
    overview_lines: list[str] = []
    if num_summary:
        # Show a couple of headline metrics from the first 3 numeric columns
        for row in num_summary[:3]:
            overview_lines.append(
                f"{row['column']}: mean={row.get('mean'):.3g}, std={row.get('std'):.3g}, "
                f"skew={row.get('skew'):.3g}"
            )

    # Key drivers
    drivers: list[str] = []
    for c in top_corr[:3]:
        drivers.append(f"{c['col_x']} and {c['col_y']} move together (|r|={c['abs_r']}).")
    if not drivers:
        drivers.append("No strong numeric drivers detected (insufficient numeric columns).")

    # Anomalies & caveats
    anomalies: list[str] = []
    if top_missing:
        anomalies.append("High missingness in key columns may bias results; consider imputation.")
    if n_cols > 60:
        anomalies.append("Wide dataset; feature selection or dimensionality reduction may help.")
    if not anomalies:
        anomalies.append("No major data quality issues detected at a glance.")

    # Recommendations
    recs: list[str] = [
        "Prioritize data cleaning for columns with highest missingness.",
        "Validate correlations with domain knowledge and downstream modeling.",
        "Standardize numeric features before modeling (z-score).",
    ]

    return {
        "executive_summary": " ".join(exec_lines),
        "data_overview": "\n".join(overview_lines) if overview_lines else "Basic overview available.",
        "key_drivers": drivers,
        "anomalies": anomalies,
        "recommendations": recs,
    }
