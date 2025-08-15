# web/Home.py
from __future__ import annotations

import time
from pathlib import Path

import streamlit as st
from _client import api_get, api_post, API  # adjust path if needed

st.set_page_config(page_title="Auto EDA)", page_icon="📊")
st.title("📊 Auto EDA & Storytelling")

# near the top of the page (under the title)
st.subheader("Presentation theme")
colA, colB = st.columns([1, 1])
with colA:
    theme = st.selectbox("Theme", ["light", "dark"], index=0, key="sel-theme")
with colB:
    color = st.color_picker("Accent color", "#1f77b4", key="sel-color")

# pass theme/color into the run call
def render_run_row(ds_id: str, label: str = "Run EDA & Generate Slides", key_prefix: str = "run"):
    col1, col2 = st.columns([4, 2])
    with col1:
        st.write(f"**Dataset ID:** `{ds_id}`")
    with col2:
        if st.button(label, key=f"{key_prefix}-{ds_id}"):
            r = api_post("/jobs/run", params={"dataset_id": ds_id, "theme": theme, "color": color})
            # ... rest unchanged ...



st.caption(f"API base: {API}")

# Health check
with st.expander("API health check", expanded=False):
    import traceback
    try:
        r = api_get("/healthz")
        st.write("GET /healthz →", r.status_code, r.text[:200])
    except Exception as e:
        st.error(f"Health check failed: {e}")
        st.code(traceback.format_exc(), language="text")

with st.expander("API endpoint", expanded=False):
    st.write("Using:", API)

# ---------------------------
# Upload CSV/XLSX
# ---------------------------
st.subheader("Upload a dataset")
uploaded = st.file_uploader("Choose CSV or XLSX", type=["csv", "xlsx"], accept_multiple_files=False)
engine = st.selectbox("XLSX engine", ["auto", "openpyxl"], index=0)
if uploaded and st.button("Upload"):
    files = {"file": (uploaded.name, uploaded.getvalue())}
    r = api_post("/datasets/upload", files=files, params={"engine": engine})
    if r.ok:
        ds = r.json()
        st.session_state["last_uploaded"] = ds
        st.success(
            f"Uploaded: **{ds['filename']}**  •  id=`{ds['dataset_id']}`  •  "
            f"rows={ds['meta']['rows']}  cols={ds['meta']['cols']}"
        )
    else:
        st.error(f"Upload failed: {r.status_code} — {r.text}")

st.divider()

# ---------------------------
# Helper: download button
# ---------------------------
def download_button_for_report(pptx_path: str):
    name = Path(pptx_path).name
    resp = api_get(f"/reports/download/{name}", stream=True)
    if not resp.ok:
        st.error(f"Download failed: {resp.status_code} — {resp.text}")
        return
    st.download_button(
        label=f"⬇️ Download {name}",
        data=resp.content,
        file_name=name,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        key=f"dl-{name}",
    )

# ---------------------------
# Helper: run one dataset
# ---------------------------
# inside web/Home.py

def render_run_row(ds_id: str, label: str = "Run EDA & Generate Slides", key_prefix: str = "run"):
    col1, col2 = st.columns([4, 2])
    with col1:
        st.write(f"**Dataset ID:** `{ds_id}`")
    with col2:
        if st.button(label, key=f"{key_prefix}-{ds_id}"):
            with st.spinner("Running pipeline..."):
                r = api_post("/jobs/run", params={"dataset_id": ds_id, "theme": theme, "color": color})

            if r.ok:
                payload = r.json()
                result = payload.get("result", {})
                logs = result.get("logs", [])

                # progress visualization (client-side since it's sync)
                stages = ["prepare-output-dir", "run-eda", "generate-narrative", "build-pptx"]
                done = {x["name"]: x for x in logs if x.get("status") == "ok"}
                pct = int(100 * min(len(done), len(stages)) / len(stages))
                st.progress(pct, text=f"Steps complete: {len(done)}/{len(stages)}")

                # show step logs
                with st.expander("Run details", expanded=False):
                    for s in logs:
                        emoji = "✅" if s["status"] == "ok" else ("❌" if s["status"] == "error" else "⏳")
                        st.write(f"{emoji} **{s['name']}** — {s['status']}")
                        if s.get("details"):
                            st.code(s["details"], language="text")

                # download when ready
                pptx_path = result.get("pptx_path")
                if pptx_path:
                    st.success("Report ready!")
                    download_button_for_report(pptx_path)
                else:
                    st.info("Pipeline finished, but no pptx produced.")

            else:
                # 500 with structured detail from the API
                try:
                    err_payload = r.json()  # {'detail': { 'error': {...}, 'logs': [...] }}
                except Exception:
                    st.error(f"API error: {r.status_code} — {r.text}")
                    return

                detail = err_payload.get("detail", {})
                logs = detail.get("logs", []) or detail.get("result", {}).get("logs", [])
                err = detail.get("error") or detail.get("result", {}).get("error")

                st.error("Pipeline failed.")
                if err and err.get("message"):
                    st.write(f"**Reason:** {err.get('message')}")
                with st.expander("Error details", expanded=False):
                    if err and err.get("traceback"):
                        st.code(err["traceback"], language="text")

                if logs:
                    with st.expander("Step logs", expanded=True):
                        for s in logs:
                            emoji = "✅" if s["status"] == "ok" else ("❌" if s["status"] == "error" else "⏳")
                            st.write(f"{emoji} **{s['name']}** — {s['status']}")
                            if s.get("details"):
                                st.code(s["details"], language="text")
            # end of button click

# ---------------------------
# Quick-run for sample
# ---------------------------
st.subheader("Quick run: sample dataset")
render_run_row("sample_dataset", label="Run sample_dataset", key_prefix="quick")

st.divider()

# ---------------------------
# List & run any stored dataset
# ---------------------------
st.subheader("Datasets in storage")
try:
    ls = api_get("/datasets/")
    st.write("GET /datasets/ →", ls.status_code)
    if ls.ok:
        items = ls.json()
        if not items:
            st.info("No datasets yet. Upload one above.")
        else:
            for row in items:
                ds_id = row["dataset_id"]
                st.write(f"- `{ds_id}` · {row['ext']} · {row['path']}")
                render_run_row(ds_id, label="Run", key_prefix="list")
    else:
        st.warning(f"API error: {ls.status_code} — {ls.text}")
except Exception as e:
    import traceback
    st.error(f"Request to {API}/datasets/ failed: {e}")
    st.code(traceback.format_exc(), language="text")

# ---------------------------
# Optional async polling (future RQ mode)
# ---------------------------
job_id = st.session_state.get("job_id")
if job_id and job_id != "sync":
    with st.spinner("Processing…"):
        for _ in range(180):  # up to ~3 min
            jr = api_get(f"/jobs/{job_id}")
            if jr.ok:
                data = jr.json()
                st.write(f"Status: **{data.get('status','?')}**")
                result = data.get("result", {})
                pptx_path = result.get("pptx_path")
                if data.get("status") == "finished" and pptx_path:
                    st.success("Report ready!")
                    download_button_for_report(pptx_path)
                    break
            time.sleep(1)
