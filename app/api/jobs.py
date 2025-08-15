# app/api/jobs.py
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from app.core.config import settings
from app.services.pipeline import run_full_pipeline

router = APIRouter()

def _storage_root() -> Path:
    return Path(settings.STORAGE_DIR)

def _resolve_dataset_path(dataset_id: str) -> Path:
    root = _storage_root()
    for p in root.glob(f"{dataset_id}.*"):
        return p
    raise HTTPException(status_code=404, detail="Dataset not found")

@router.post("/run")
def run_job(
    dataset_id: str = Query(..., description="ID part of stored file name"),
    theme: str = Query("light", pattern="^(light|dark)$"),
    color: str = Query("#1f77b4"),
):
    """
    Sync pipeline with logs and error surfacing.
    """
    dataset_path = _resolve_dataset_path(dataset_id)
    result = run_full_pipeline(str(dataset_path), str(_storage_root()), theme=theme, color=color)

    # if pipeline signaled an error, return 500 with details to the UI
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result)

    return {"job_id": "sync", "status": "finished", "result": result}
