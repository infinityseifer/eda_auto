# app/api/reports.py
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter()

def _reports_dir() -> Path:
    p = Path(settings.STORAGE_DIR) / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p

@router.get("/download/{name}")
def download_report(name: str):
    # Security: prevent path traversal
    safe = Path(name).name
    path = _reports_dir() / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=safe,
    )
