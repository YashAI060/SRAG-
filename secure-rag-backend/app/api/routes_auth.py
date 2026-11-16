"""
Auth routes — with tenant_id embedded in JWT server-side.

Security principle:
    tenant_id = current_user.email (server-derived at login)
    NEVER accepted from the client request body.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from passlib.context import CryptContext

from app.core.security import create_access_token
from app.models.database import get_db, User
from app.models.schemas import UserCreate, UserResponse, Token
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash(password: str) -> str:
    return _pwd_ctx.hash(password)


def _verify(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user. tenant_id = user's email (set server-side)."""
    result = await db.execute(
        select(User).where(
            (User.username == user_in.username) | (User.email == user_in.email)
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=_hash(user_in.password),
        role=user_in.role,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login and receive a JWT with embedded tenant_id (email) and role."""
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalars().first()

    if not user or not _verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # tenant_id is the user's email — server-owned, never client-controllable
    token = create_access_token(
        subject=user.username,
        role=user.role,
        tenant_id=user.email,
    )
    return Token(
        access_token=token,
        token_type="bearer",
        tenant_id=user.email,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the current authenticated user's profile."""
    result = await db.execute(select(User).where(User.username == current_user["sub"]))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
