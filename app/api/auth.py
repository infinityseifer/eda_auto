"""Auth endpoints: register, login, and current user.

- POST /auth/register
- POST /auth/login
- GET  /auth/me

Also ensures the `user` table exists at startup when the router is included.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, db_sess
from app.core.security import hash_password, verify_password, create_access_token
from app.main import app
from app.models.user import get_user_by_email, create_user, User, ensure_tables

router = APIRouter()


@router.on_event("startup")
def _ensure_user_table():
    """Create the `user` table on app startup if possible."""
    engine = getattr(app.state, "db_engine", None)
    if engine is not None:
        try:
            ensure_tables(engine)
        except Exception:
            # Non-fatal in MVP; health checks will still reflect DB readiness
            pass


# --- Schemas ----------------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: EmailStr

    @classmethod
    def from_orm_user(cls, u: User) -> "UserOut":
        return cls(id=u.id, email=u.email)


# --- Routes -----------------------------------------------------------------------------
@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, db: Annotated[Session, Depends(db_sess)]):
    """Create a new user with a bcrypt-hashed password."""
    if get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    u = create_user(
        db,
        user_id=str(uuid.uuid4()),
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    return UserOut.from_orm_user(u)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Annotated[Session, Depends(db_sess)]):
    """Issue a JWT if email/password are valid."""
    u = get_user_by_email(db, payload.email)
    if not u or not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": u.id})
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current: Annotated[User, Depends(get_current_user)]):
    """Return the current authenticated user."""
    return UserOut.from_orm_user(current)
