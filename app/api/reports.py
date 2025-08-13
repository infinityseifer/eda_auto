"""Report listing and download endpoints.

For MVP scaffold, report are discovered by scanning STORAGE_DIR for files
matching `report_*.pptx`. Later, this should query a database table.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.main import app

router = APIRouter()


def _storage() -> Path:
    return Path(getattr(app.state, "storage_dir", "./storage"))


@router.get("")
def list_report() -> list[dict]:
    """List available PPTX report by scanning storage."""
    root = _storage()
    root.mkdir(parents=True, exist_ok=True)
    out = []
    for p in root.glob("report_*.pptx"):
        out.append({"name": p.name, "path": str(p), "size": p.stat().st_size})
    return out


@router.get("/download/{filename}")
def download_report(filename: str):
    """Send a generated PPTX back to the client by filename.

    Parameters
    ----------
    filename:
        The base filename (e.g., ``report_abcd.pptx``). Only files inside STORAGE_DIR
        and matching the `report_*.pptx` pattern are served.
    """
    path = _storage() / filename
    if not path.exists() or not path.name.startswith("report_") or path.suffix.lower() != ".pptx":
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename=path.name)
