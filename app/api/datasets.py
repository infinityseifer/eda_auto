# app/api/datasets.py
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.main import app

router = APIRouter()

ALLOWED_EXTS: set[str] = {".csv", ".xlsx"}
MAX_SIZE_MB: int = 50


def _storage_root() -> Path:
    return Path(getattr(app.state, "storage_dir", "./storage"))


@router.get("/")  # GET /datasets/
def list_datasets():
    """
    List uploaded datasets by scanning the storage directory.
    Returns [{dataset_id, path, ext}]
    """
    root = _storage_root()
    root.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, str]] = []
    for p in root.glob("*.*"):
        if p.suffix.lower() in ALLOWED_EXTS:
            out.append({"dataset_id": p.stem, "path": str(p), "ext": p.suffix})
    return out


@router.post("/upload")  # POST /datasets/upload
async def upload_dataset(
    file: UploadFile = File(..., description="CSV or XLSX"),
    engine: Literal["openpyxl", "auto"] = "auto",
):
    """
    Upload a dataset, validate type/size, persist to storage, and return metadata.
    - Supports .csv and .xlsx
    - Reads a small sample to infer rows/columns
    """
    # Validate extension
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {sorted(ALLOWED_EXTS)}")

    # Size check
    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large: {size_mb:.1f} MB > {MAX_SIZE_MB} MB")

    # Persist to disk
    root = _storage_root()
    root.mkdir(parents=True, exist_ok=True)
    dataset_id = str(uuid.uuid4())
    out_path = root / f"{dataset_id}{ext}"
    out_path.write_bytes(data)

    # Light metadata
    try:
        if ext == ".csv":
            df = pd.read_csv(out_path, nrows=100_000)
        else:
            # choose an engine if requested; otherwise let pandas auto-pick
            read_kwargs = {"nrows": 100_000}
            if engine == "openpyxl":
                read_kwargs["engine"] = "openpyxl"
            df = pd.read_excel(out_path, **read_kwargs)
        meta = {"rows": int(df.shape[0]), "cols": int(df.shape[1])}
    except Exception as e:
        # Clean up the bad upload
        try:
            out_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse file: {e}. "
                   f"Tips: ensure the file is a valid {ext.upper()} and not password-protected.",
        )

    return {
        "dataset_id": dataset_id,
        "filename": filename,
        "stored_at": str(out_path),
        "size_mb": round(size_mb, 3),
        "meta": meta,
    }
