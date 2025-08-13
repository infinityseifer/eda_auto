"""
Job orchestration endpoints for EDA & slide generation.
- If USE_REDIS=true **and** a queue is available -> enqueue with RQ
- Otherwise -> run synchronously (no Redis required)
"""
from __future__ import annotations

import os
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


def _queue():
    return getattr(app.state, "rq_queue", None)


@router.post("/run")
def run_job(dataset_id: str):
    """
    Run the pipeline:
      - enqueue if USE_REDIS=true and queue available
      - else, run synchronously and return result immediately
    """
    dataset_path = _resolve_dataset_path(dataset_id)
    use_redis = os.getenv("USE_REDIS", "false").lower() in {"1", "true", "yes"}

    from app.services.pipeline import run_full_pipeline

    q = _queue()
    if use_redis and q is not None:
        job = q.enqueue(run_full_pipeline, str(dataset_path), str(_storage_root()), job_timeout=900)
        return {"job_id": job.get_id(), "status": "queued", "dataset_path": str(dataset_path)}

    # Fallback: sync mode
    try:
        result = run_full_pipeline(str(dataset_path), str(_storage_root()))
        return {"job_id": "sync", "status": "finished", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")


@router.get("/{job_id}")
def job_status(job_id: str):
    """
    Status endpoint. In sync mode, returns finished immediately.
    """
    if job_id == "sync":
        return {"id": "sync", "status": "finished", "result": None}

    q = _queue()
    if q is None:
        # queue not in use; there's no async job to report on
        raise HTTPException(status_code=404, detail="Job not found")

    j = q.fetch_job(job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": j.id,
        "status": j.get_status(),
        "result": j.result if j.is_finished else None,
        "enqueued_at": getattr(j, "enqueued_at", None),
        "ended_at": getattr(j, "ended_at", None),
    }
