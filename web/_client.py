"""Thin HTTP client helpers for the Streamlit UI.

Reads API base URL from the `API_URL` environment variable; defaults to http://127.0.0.1:8000
"""
from __future__ import annotations

import os
import requests

API_VERSION = "1.1.0"


# web/_client.py
API = "http://127.0.0.1:8000"  # force local API for now



def api_post(path: str, **kwargs):
    return requests.post(f"{API}{path}", timeout=120, **kwargs)


def api_get(path: str, **kwargs):
    return requests.get(f"{API}{path}", timeout=120, **kwargs)