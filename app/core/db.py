"""Database utilities for the Auto-EDA MVP.

This module centralizes SQLAlchemy setup: engine creation, session factory, and a FastAPI
dependency to yield per-request sessions.

Functions
---------
init_engine_and_session(url: str) -> tuple[Engine, sessionmaker]:
    Create an Engine and a session factory.

get_db():
    FastAPI dependency that `yield`s a session and ensures cleanup.
"""
from __future__ import annotations

from typing import Tuple

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


def init_engine_and_session(url: str) -> Tuple[Engine, sessionmaker]:
    """Initialize SQLAlchemy engine and session factory.

    Parameters
    ----------
    url:
        SQLAlchemy database URL. Example:
        ``postgresql+psycopg2://user:pass@host:5432/db`` or ``sqlite:///./dev.db``

    Returns
    -------
    (engine, SessionLocal)
        A tuple containing the Engine and a configured sessionmaker.
    """
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, SessionLocal


def get_db(SessionLocal: sessionmaker):
    """Create a FastAPI dependency that yields a DB session.

    Usage (inside a router):
        >>> from fastapi import Depends
        >>> db = Depends(get_db(app.state.SessionLocal))
    """
    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    return _get_db
