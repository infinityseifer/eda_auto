# web/Home.py
"""
Streamlit UI — Minimal runner for the built-in sample dataset only.
- Triggers: POST /jobs/run?dataset_id=sample_dataset
- If sync result returns a PPTX path, shows a Download button (streams bytes).
"""
from __future__ import annotations

from pathlib import Path
import streamlit as st

# If _client.py sits in the same folder as this file, this import is correct.
# If it's in a package (web/_client.py), change to: from web._client import api_get, api_post, API
from _client import api_get, api_post, API

st.set_page_config(page_title="Auto EDA — Sample Dataset", page_icon="📊")
st.title("📊 Auto EDA — Sample Dataset")

SAMPLE_ID = "sample_dataset"

st.write("This page runs the pipeline **only** for the bundled sample dataset.")
st.code(f"dataset_id = '{SAMPLE_ID}'", language="python")

def download_button_for_report(pptx_path: str):
    """Fetch PPTX bytes from API and render a Streamlit download button."""
    name = Path(pptx_path).name
    resp = api_get(f"/reports/download/{name}", stream=True)
    if not resp.ok:
        st.error(f"Download failed: {resp.status_code} — {resp.text}")
        return
    st.download_button(
        label=f"⬇️ Download {name}",
        data=resp.content,  # bytes
        file_name=name,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        key=f"dl-{name}",
    )

# Optional: show whether the sample file is present in storage (nice sanity check)
ls = api_get("/datasets/")
if ls.ok:
    items = {row["dataset_id"] for row in ls.json()}
    if SAMPLE_ID not in items:
        st.warning("`sample_dataset` not found in storage. Make sure the file exists as `storage/sample_dataset.csv` (or .xlsx).")
else:
    st.info("API is not reachable yet. Start FastAPI or check API_URL at the top of _client.py.")

# Main action
if st.button("Run EDA & Generate Slides for sample_dataset"):
    r = api_post("/jobs/run", params={"dataset_id": SAMPLE_ID})
    if not r.ok:
        st.error(f"API error: {r.status_code} — {r.text}")
    else:
        payload = r.json()
        job_id = payload.get("job_id")
        if job_id == "sync":  # dev mode: finished immediately
            result = payload.get("result", {})
            pptx_path = result.get("pptx_path")
            if pptx_path:
                st.success("Report ready!")
                download_button_for_report(pptx_path)
            else:
                st.info("Pipeline finished, but no pptx_path returned.")
        else:
            # If you later enable Redis/async, you could poll /jobs/{job_id} here.
            st.info(f"Queued job: {job_id}")
