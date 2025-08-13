"""User model and CRUD helpers for simple auth.

This MVP uses a single `user` table with bcrypt password hashes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session


class Base(DeclarativeBase):
    """Declarative base for ORM models."""
    pass


class User(Base):
    """User table storing email and hashed password."""
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def ensure_tables(engine) -> None:
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


# --- CRUD helpers ----------------------------------------------------------------------

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_id: str, email: str, password_hash: str) -> User:
    u = User(id=user_id, email=email, password_hash=password_hash)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

