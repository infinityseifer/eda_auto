"""Common FastAPI dependencies (DB session, current user).

Provides:
- `db_sess`: yields a SQLAlchemy session from the app's SessionLocal
- `get_current_user`: OAuth2 bearer auth that decodes a JWT and loads a `User`
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token, TokenError
from app.main import app
from app.models.user import User, get_user_by_id

# OAuth2 password flow (token URL handled by /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def db_sess() -> Session:
    """Yield a SQLAlchemy session using the application's SessionLocal."""
    SessionLocal = getattr(app.state, "SessionLocal", None)
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return next(get_db(SessionLocal)())


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(db_sess)],
) -> User:
    """Validate a bearer token and load the associated user from the DB."""
    try:
        claims = decode_access_token(token)
    except TokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    user_id = claims.get("sub")
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
