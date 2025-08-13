# app/api/jobs.py
"""
DEV MODE: run the EDA pipeline synchronously (no Redis/RQ required).
"""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.main import app

router = APIRouter()

def _storage_root() -> Path:
    return Path(getattr(app.state, "storage_dir", "./storage"))

def _resolve_dataset_path(dataset_id: str) -> Path:
    root = _storage_root()
    for p in root.glob(f"{dataset_id}.*"):
        return p
    raise HTTPException(status_code=404, detail="Dataset not found")

@router.post("/run")
def run_job(dataset_id: str):
    """
    Run the full pipeline inline and return the result immediately.
    """
    dataset_path = _resolve_dataset_path(dataset_id)
    try:
        from app.services.pipeline import run_full_pipeline
        result = run_full_pipeline(str(dataset_path), str(_storage_root()))
        return {"job_id": "sync", "status": "finished", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")

@router.get("/{job_id}")
def job_status(job_id: str):
    """
    Kept for UI compatibility. In sync mode there's nothing to poll.
    """
    if job_id == "sync":
        return {"id": "sync", "status": "finished", "result": None}
    raise HTTPException(status_code=404, detail="Job not found")
