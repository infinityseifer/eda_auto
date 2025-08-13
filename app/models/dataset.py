"""
Dataset model and CRUD helpers.

This module defines the SQLAlchemy ORM model for uploaded datasets and
convenience functions to create, fetch, list, and delete them.

It reuses the shared Declarative `Base` from app.models.user to keep all
tables under a single metadata for migrations and create_all().
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Iterable, List

from sqlalchemy import String, DateTime, Integer, BigInteger, select, delete
from sqlalchemy.orm import Mapped, mapped_column, Session

# Reuse the shared Base to keep one metadata across models
from app.models.user import Base


class Dataset(Base):
    """
    Dataset table:

    - id:          UUID (as string) primary key
    - user_id:     Optional owner/user id (string) if you add auth scoping
    - original_name: Original filename provided by the client (e.g., "sales.csv")
    - stored_path: Absolute or project-relative path to the stored file
    - ext:         File extension (".csv", ".xlsx")
    - mime_type:   Best-effort MIME type (e.g., "text/csv")
    - size_bytes:  File size on disk
    - rows:        Parsed row count (if known)
    - cols:        Parsed column count (if known)
    - created_at:  Upload time (server clock, UTC)
    """
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)

    original_name: Mapped[str] = mapped_column(String(255), index=True)
    stored_path: Mapped[str] = mapped_column(String(1024))

    ext: Mapped[str] = mapped_column(String(16), index=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cols: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Optional: friendly string representation
    def __repr__(self) -> str:
        return (
            f"Dataset(id={self.id!r}, name={self.original_name!r}, ext={self.ext!r}, "
            f"rows={self.rows}, cols={self.cols}, created_at={self.created_at})"
        )


# ---------------------------
# CRUD convenience functions
# ---------------------------

def create_dataset(
    db: Session,
    *,
    dataset_id: str,
    original_name: str,
    stored_path: str,
    ext: str,
    mime_type: Optional[str] = None,
    size_bytes: Optional[int] = None,
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    user_id: Optional[str] = None,
) -> Dataset:
    """
    Insert a new Dataset row and return it.
    """
    ds = Dataset(
        id=dataset_id,
        user_id=user_id,
        original_name=original_name,
        stored_path=stored_path,
        ext=ext,
        mime_type=mime_type,
        size_bytes=size_bytes,
        rows=rows,
        cols=cols,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def get_dataset(db: Session, dataset_id: str) -> Optional[Dataset]:
    """
    Fetch a Dataset by id.
    """
    return db.get(Dataset, dataset_id)


def list_datasets(
    db: Session,
    *,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dataset]:
    """
    List datasets, optionally scoped by user_id.
    """
    stmt = select(Dataset).order_by(Dataset.created_at.desc())
    if user_id:
        stmt = stmt.where(Dataset.user_id == user_id)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def delete_dataset(db: Session, dataset_id: str) -> int:
    """
    Delete a dataset by id. Returns the number of rows deleted (0 or 1).
    """
    stmt = delete(Dataset).where(Dataset.id == dataset_id)
    res = db.execute(stmt)
    db.commit()
    return res.rowcount or 0
