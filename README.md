# Auto EDA & Storytelling (MVP)

**v1.0.0** — Streamlit UI + FastAPI backend. Runs EDA on a built-in `sample_dataset` and generates a PPTX with narrative slides.

## Run (dev)
```bash
# API
uvicorn app.main:app --reload --port 8000

# UI (in another terminal)
streamlit run web/Home.py --server.port 8501
