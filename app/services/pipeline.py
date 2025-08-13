# app/services/pipeline.py
from __future__ import annotations
import os, uuid
from app.services.eda import run_eda
from app.services.narrative import generate_narrative
from app.services.pptx_builder import build_pptx

def run_full_pipeline(dataset_path: str, storage_dir: str) -> dict:
    eda = run_eda(dataset_path)
    narrative = generate_narrative(eda)
    out = os.path.join(storage_dir, f"report_{uuid.uuid4()}.pptx")
    build_pptx(narrative, eda.get("charts", {}), out)
    return {"pptx_path": out, "stats": eda.get("stats", {})}
