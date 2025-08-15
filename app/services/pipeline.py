# app/services/pipeline.py
"""
Pipeline: EDA -> Narrative -> PPTX builder.
Used by /jobs/run to execute the whole flow (sync in dev).
"""
from __future__ import annotations

from pathlib import Path

from app.services.eda import run_eda
from app.services.narrative import generate_narrative
from app.services.pptx_builder import build_presentation
from app.core.config import settings


def run_full_pipeline(
    dataset_path: str,
    storage_root: str,
    *,
    theme: str = "light",
    color: str = "#1f77b4",
) -> dict:
    """Run the entire pipeline and return {'pptx_path': ...}."""
    reports_dir = Path(settings.STORAGE_DIR) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    eda = run_eda(dataset_path)
    narrative = generate_narrative(eda)

    pptx_path = build_presentation(
        eda=eda,
        narrative=narrative,
        out_dir=str(reports_dir),
        theme=theme,
        color=color,
    )
    return {"pptx_path": pptx_path}
