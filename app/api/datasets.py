from __future__ import annotations
import uuid
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.main import app

router = APIRouter()
ALLOWED_EXTS = {".csv", ".xlsx"}
MAX_SIZE_MB = 50

def _storage_root() -> Path:
    return Path(getattr(app.state, "storage_dir", "./storage"))

@router.get("/")  # -> /datasets/
def list_datasets():
    root = _storage_root(); root.mkdir(parents=True, exist_ok=True)
    out = []
    for p in root.glob("*.*"):
        if p.suffix.lower() in ALLOWED_EXTS:
            out.append({"dataset_id": p.stem, "path": str(p), "ext": p.suffix})
    return out

@router.post("/upload")  # -> /datasets/upload
async def upload_dataset(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    data = await file.read()
    size_mb = len(data)/(1024*1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large: {size_mb:.1f} MB > {MAX_SIZE_MB} MB")
    root = _storage_root(); root.mkdir(parents=True, exist_ok=True)
    dataset_id = str(uuid.uuid4())
    out_path = root / f"{dataset_id}{ext}"
    out_path.write_bytes(data)
    try:
        df = pd.read_csv(out_path, nrows=50000) if ext == ".csv" else pd.read_excel(out_path, nrows=50000)
        meta = {"rows": int(df.shape[0]), "cols": int(df.shape[1])}
    except Exception as e:
        try: out_path.unlink(missing_ok=True)
        except Exception: pass
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")
    return {"dataset_id": dataset_id, "filename": file.filename, "stored_at": str(out_path),
            "size_mb": round(size_mb,3), "meta": meta}
