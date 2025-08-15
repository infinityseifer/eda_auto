# app/services/eda.py
"""EDA service for Auto-EDA MVP.

Functions
---------
run_eda(dataset_path: str, sample_rows: int | None = 50000, max_cols: int = 100) -> dict
    Loads a dataset (CSV/XLSX), performs lightweight profiling, and exports core charts.

Notes
-----
- Uses pandas and matplotlib only (no seaborn) for portability.
- Saves chart PNGs under `<storage_dir>/images/<dataset_id>/`.
- Returns a dict with `stats` and `charts` (mapping title -> file path).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# Headless backend to avoid GUI warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Import settings directly to avoid circular imports with app.main
from app.core.config import settings


# ----------------------------- Config ------------------------------------------
@dataclass
class EDAConfig:
    sample_rows: int | None = 50_000
    max_numeric_hists: int = 4
    max_categorical_bars: int = 4
    corr_top_k: int = 20


# ----------------------------- Helpers -----------------------------------------
def _storage_root() -> Path:
    return Path(settings.STORAGE_DIR)


def _img_dir(dataset_id: str) -> Path:
    p = _storage_root() / "images" / dataset_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load_df(path: str, nrows: int | None) -> pd.DataFrame:
    path_lower = path.lower()
    if path_lower.endswith(".csv"):
        return pd.read_csv(path, nrows=nrows)
    elif path_lower.endswith(".xlsx") or path_lower.endswith(".xls"):
        # Let pandas choose engine; user can install openpyxl if needed
        return pd.read_excel(path, nrows=nrows)
    else:
        # Try CSV as a last resort
        return pd.read_csv(path, nrows=nrows)


def _coerce_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Try common date formats first, then generic parsing if ≥90% parse rate."""
    common_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]
    for c in df.columns:
        if df[c].dtype == object:
            col = df[c]
            parsed = None
            for fmt in common_formats:
                try:
                    parsed = pd.to_datetime(col, format=fmt, errors="coerce")
                    if parsed.notna().mean() > 0.9:
                        df[c] = parsed
                        break
                except Exception:
                    parsed = None
            else:
                # Fallback to generic parsing (dateutil); keep only if consistent
                try:
                    parsed = pd.to_datetime(col, errors="coerce")
                    if parsed.notna().mean() > 0.9:
                        df[c] = parsed
                except Exception:
                    pass
    return df


def _top_categories(df: pd.DataFrame, max_cols: int = 4) -> List[Tuple[str, List[Tuple[str, int]]]]:
    out: List[Tuple[str, List[Tuple[str, int]]]] = []
    for c in df.select_dtypes(include=["object", "category"]).columns:
        vc = df[c].astype("object").fillna("<NA>").value_counts().head(10)
        out.append((c, list(zip(vc.index.astype(str).tolist(), vc.values.tolist()))))
        if len(out) >= max_cols:
            break
    return out


def _numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    num = df.select_dtypes(include=[np.number])
    if num.empty:
        return pd.DataFrame()
    desc = num.describe().T
    # Explicit numeric_only guards for newer pandas
    desc["skew"] = num.skew(numeric_only=True)
    desc["kurtosis"] = num.kurtosis(numeric_only=True)
    return desc.reset_index().rename(columns={"index": "column"})


def _correlation_pairs(df: pd.DataFrame, top_k: int = 20):
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] < 2:
        return []
    corr = num.corr(numeric_only=True).abs()
    pairs: List[Tuple[str, str, float]] = []
    cols = corr.columns
    for i in range(1, len(cols)):
        for j in range(i):
            pairs.append((cols[i], cols[j], float(corr.iloc[i, j])))
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs[:top_k]


def _save_plot(fig, path: Path):
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)  # always close to avoid backend warnings


def _histogram(imgdir: Path, df: pd.DataFrame, col: str) -> Path:
    fig = plt.figure(figsize=(7, 4))
    s = df[col].dropna()
    plt.hist(s, bins=30)
    plt.title(f"Distribution of {col}")
    plt.xlabel(col)
    plt.ylabel("Count")
    out = imgdir / f"hist_{col}.png"
    _save_plot(fig, out)
    return out


def _bar_topk(imgdir: Path, df: pd.DataFrame, col: str, k: int = 10) -> Path:
    fig = plt.figure(figsize=(7, 4))
    vc = df[col].astype("object").fillna("<NA>").value_counts().head(k)
    plt.bar(vc.index.astype(str), vc.values)
    plt.title(f"Top {k} {col}")
    plt.xlabel(col)
    plt.ylabel("Count")
    plt.xticks(rotation=30, ha="right")
    out = imgdir / f"bar_{col}.png"
    _save_plot(fig, out)
    return out


def _missingness_heatmap(imgdir: Path, df: pd.DataFrame) -> Path | None:
    miss = df.isna()
    if miss.sum().sum() == 0:
        return None
    fig = plt.figure(figsize=(7, 4))
    plt.imshow(miss.values, aspect="auto")
    plt.title("Missingness by row/column")
    plt.xlabel("Columns")
    plt.ylabel("Rows (sample)")
    out = imgdir / "missingness.png"
    _save_plot(fig, out)
    return out


def _corr_heatmap(imgdir: Path, df: pd.DataFrame) -> Path | None:
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] < 2:
        return None
    corr = num.corr(numeric_only=True)
    fig = plt.figure(figsize=(7, 6))
    plt.imshow(corr.values, interpolation="nearest")
    plt.title("Correlation heatmap")
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
    plt.yticks(range(len(corr.columns)), corr.columns)
    out = imgdir / "correlation.png"
    _save_plot(fig, out)
    return out


# ----------------------------- Public API --------------------------------------
def run_eda(dataset_path: str, sample_rows: int | None = 50_000, max_cols: int = 100) -> dict:
    """Run lightweight EDA and export core charts.

    Parameters
    ----------
    dataset_path : str
        Path to CSV or XLSX.
    sample_rows : int | None
        If provided and the dataset is larger, a sample is taken for charting.
    max_cols : int
        Guardrail to avoid overwhelming plots on very wide dataset.

    Returns
    -------
    dict
        {
          "dataset_id": str,
          "stats": {...},
          "charts": {title: filepath, ...}
        }
    """
    dataset_id = Path(dataset_path).stem
    imgdir = _img_dir(dataset_id)

    # Load & coerce
    df = _load_df(dataset_path, nrows=sample_rows)
    df = _coerce_datetime(df)

    # Basic stats
    stats: Dict[str, object] = {
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "columns": df.columns.tolist()[:max_cols],
        "dtypes": {c: str(df[c].dtype) for c in df.columns[:max_cols]},
        "missing_by_col": df.isna().sum().sort_values(ascending=False).head(20).to_dict(),
    }

    num_summary = _numeric_summary(df)
    stats["numeric_summary"] = (
        num_summary.head(50).to_dict(orient="records") if not num_summary.empty else []
    )

    top_pairs = _correlation_pairs(df, top_k=EDAConfig.corr_top_k)
    stats["top_correlations"] = [
        {"col_x": a, "col_y": b, "abs_r": round(r, 3)} for a, b, r in top_pairs
    ]

    # Charts
    charts: Dict[str, str] = {}

    miss = _missingness_heatmap(imgdir, df)
    if miss:
        charts["Missingness"] = str(miss)

    corr = _corr_heatmap(imgdir, df)
    if corr:
        charts["Correlation heatmap"] = str(corr)

    # Numeric histograms
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:max_cols]
    for col in num_cols[: EDAConfig.max_numeric_hists]:
        p = _histogram(imgdir, df, col)
        charts[f"Distribution — {col}"] = str(p)

    # Categorical bars
    for col, _ in _top_categories(df, max_cols=EDAConfig.max_categorical_bars):
        p = _bar_topk(imgdir, df, col)
        charts[f"Top categories — {col}"] = str(p)

    return {"dataset_id": dataset_id, "stats": stats, "charts": charts}
