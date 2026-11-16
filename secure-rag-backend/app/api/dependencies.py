"""
FastAPI dependencies — real JWT verification.

CRITICAL: tenant_id is extracted from the verified JWT payload.
It is NEVER read from the request body or query string.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Verify Bearer token and return decoded claims.
    Returned dict contains: sub, role, tenant_id
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
        return payload  # {"sub": ..., "role": ..., "tenant_id": ..., "exp": ...}
    except JWTError:
        raise credentials_exception


class RoleChecker:
    """Dependency that enforces role-based access control."""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.get('role')}' is not permitted for this action.",
            )
        return current_user
