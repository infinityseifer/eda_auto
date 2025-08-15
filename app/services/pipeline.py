# app/services/pipeline.py
"""
Pipeline: EDA -> Narrative -> PPTX builder (sync, with step logs & error surfacing).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any
import traceback
import time

from app.services.eda import run_eda
from app.services.narrative import generate_narrative
from app.services.pptx_builder import build_presentation

@dataclass
class StepLog:
    name: str
    status: str  # "ok" | "error"
    started_at: float
    ended_at: float | None = None
    details: str | None = None

    def finish(self, status: str = "ok", details: str | None = None) -> None:
        self.status = status
        self.ended_at = time.time()
        if details:
            self.details = details

def _start(steps: List[StepLog], name: str) -> StepLog:
    s = StepLog(name=name, status="running", started_at=time.time(), ended_at=None)
    steps.append(s)
    return s

def run_full_pipeline(
    dataset_path: str,
    storage_root: str,
    *,
    theme: str = "light",
    color: str = "#1f77b4",
) -> Dict[str, Any]:
    """
    Run the pipeline and return:
      {
        "pptx_path": "<filename or path>",
        "logs": [StepLog...],
        "error": {"message": str, "traceback": str}  # only if failed
      }
    """
    steps: List[StepLog] = []
    try:
        # Ensure reports dir exists
        s = _start(steps, "prepare-output-dir")
        reports_dir = Path(storage_root) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        s.finish("ok", f"reports_dir={reports_dir}")

        # EDA
        s = _start(steps, "run-eda")
        eda = run_eda(dataset_path)
        s.finish("ok", f"rows={eda['stats']['n_rows']} cols={eda['stats']['n_cols']}")

        # Narrative
        s = _start(steps, "generate-narrative")
        narrative = generate_narrative(eda)
        s.finish("ok", "narrative-ready")

        # PPTX
        s = _start(steps, "build-pptx")
        pptx_path = build_presentation(
            eda=eda,
            narrative=narrative,
            out_dir=str(reports_dir),
            theme=theme,
            color=color,
        )
        s.finish("ok", f"pptx={pptx_path}")

        return {
            "pptx_path": pptx_path,
            "logs": [asdict(x) for x in steps],
        }

    except Exception as e:
        # close out the last running step as error
        if steps and steps[-1].status == "running":
            steps[-1].finish("error", details=str(e))
        tb = traceback.format_exc()
        return {
            "pptx_path": None,
            "logs": [asdict(x) for x in steps],
            "error": {
                "message": str(e),
                "traceback": tb[-3000:],  # cap size
            },
        }
