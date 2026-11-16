"""
Security utilities: JWT creation and verification.
Tenant identity is ALWAYS derived from the authenticated token,
never from client-supplied request parameters.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from app.core.config import settings


def create_access_token(
    subject: str,
    role: str,
    tenant_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT containing the user's identity, role, and tenant.
    The tenant_id is embedded in the token at login time — clients cannot
    override it by passing a different value in request bodies.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,          # username / email
        "role": role,
        "tenant_id": tenant_id,  # server-owned; never trust from client
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify JWT. Returns the full claims dict.
    Raises jose.JWTError on invalid/expired tokens.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
