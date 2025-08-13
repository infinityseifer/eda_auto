"""Streamlit UI — report page

Features
--------
- Lists generated PowerPoint files
- Provides direct download links to `/report/download/{name}`
"""
from __future__ import annotations

import os
import streamlit as st
from web._client import api_get, API

st.set_page_config(page_title="Auto EDA — report", page_icon="📑")
st.title("📑 Generated report")

res = api_get("/report")
if not res.ok:
    st.error(res.text)
else:
    items = res.json()
    if not items:
        st.info("No report yet. Generate one from the Home page.")
    for r in items:
        name = r["name"]
        url = f"{API}/report/download/{name}"
        st.markdown(f"**{name}** — {r['size']} bytes  •  [Download]({url})")