"""
Authentication and User management routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.database import get_db
from app.db.models import UserDB, UserRole
from app.models.user import UserCreate, UserResponse, Token
from app.utils.security import get_password_hash, verify_password, create_access_token, get_current_user, admin_required

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    payload: UserCreate, 
    db: AsyncSession = Depends(get_db),
    _current_user: UserDB = Depends(admin_required)
):
    """Register a new user (Admin only)."""
    # Check if user exists
    result = await db.execute(select(UserDB).where(UserDB.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    result = await db.execute(select(UserDB).where(UserDB.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = UserDB(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info(f"User registered: {new_user.username} with role {new_user.role}")
    return new_user

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    """Standard OAuth2 login flow, returns a JWT."""
    result = await db.execute(select(UserDB).where(UserDB.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserDB = Depends(get_current_user)):
    """Return the profile of the currently logged-in user."""
    return current_user
