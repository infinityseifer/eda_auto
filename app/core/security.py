"""
Security utilities for Auto-EDA MVP.

Responsibilities
----------------
- Password hashing & verification (bcrypt via passlib)
- JWT access token creation & decoding

Usage
-----
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

hashed = hash_password("secret")
assert verify_password("secret", hashed) is True

token = create_access_token({"sub": "user_123"})
claims = decode_access_token(token)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from passlib.context import CryptContext

from app.core.config import settings


# -----------------------------------------------------------------------------
# Password hashing (bcrypt via passlib)
# -----------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Parameters
    ----------
    password : str
        Plaintext password.

    Returns
    -------
    str
        A salted bcrypt hash suitable for storage.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    return _pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Parameters
    ----------
    plain_password : str
        User-provided password attempt.
    password_hash : str
        Stored bcrypt hash.

    Returns
    -------
    bool
        True if the password matches; False otherwise.
    """
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


# -----------------------------------------------------------------------------
# JWT helpers (access tokens)
# -----------------------------------------------------------------------------
class TokenError(Exception):
    """Raised when JWT decoding/validation fails."""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    claims: Dict[str, Any],
    expires_minutes: int | None = None,
    *,
    secret: str | None = None,
    algorithm: str | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Parameters
    ----------
    claims : dict
        Public claims to embed (e.g., {"sub": "user_id"}).
    expires_minutes : int | None
        Minutes until expiry. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.
    secret : str | None
        Override signing secret (defaults to settings.JWT_SECRET).
    algorithm : str | None
        Override signing algorithm (defaults to settings.JWT_ALGORITHM).

    Returns
    -------
    str
        Encoded JWT as a compact string.
    """
    if "sub" not in claims:
        # 'sub' (subject) helps downstream identify the principal
        raise ValueError("Token claims must include a 'sub' field.")

    secret = secret or settings.JWT_SECRET
    algorithm = algorithm or settings.JWT_ALGORITHM
    exp_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES

    now = _now_utc()
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }

    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(
    token: str,
    *,
    secret: str | None = None,
    algorithms: list[str] | None = None,
) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Parameters
    ----------
    token : str
        Encoded JWT.
    secret : str | None
        Override secret (defaults to settings.JWT_SECRET).
    algorithms : list[str] | None
        Allowed algorithms. Defaults to [settings.JWT_ALGORITHM].

    Returns
    -------
    dict
        Decoded claims.

    Raises
    ------
    TokenError
        If the token is expired, invalid, or has a bad signature.
    """
    secret = secret or settings.JWT_SECRET
    algorithms = algorithms or [settings.JWT_ALGORITHM]

    try:
        return jwt.decode(token, secret, algorithms=algorithms, options={"require": ["exp", "iat", "nbf"]})
    except jwt.ExpiredSignatureError as e:
        raise TokenError("Token has expired.") from e
    except jwt.InvalidTokenError as e:
        raise TokenError("Invalid token.") from e
