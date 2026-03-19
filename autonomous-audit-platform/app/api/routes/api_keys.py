"""
CRUD routes for managing API keys.

Endpoints:
    POST   /api/api_keys        — Add a new key (Admin only)
    GET    /api/api_keys        — List all keys (Authenticated users)
    PATCH  /api/api_keys/{id}   — Update key settings (Admin only)
    DELETE /api/api_keys/{id}   — Remove a key (Admin only)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.database import get_db
from app.db.models import APIKeyDB, UserDB
from app.models.api_key import APIKeyCreate, APIKeyResponse, APIKeyUpdate
from app.utils.security import get_current_user, admin_required

router = APIRouter(prefix="/api/api_keys", tags=["API Key Manager"])


@router.post("/", response_model=APIKeyResponse, status_code=201)
async def add_api_key(
    payload: APIKeyCreate, 
    db: AsyncSession = Depends(get_db),
    _user: UserDB = Depends(admin_required)
):
    """Add a new API key for a provider."""
    key = APIKeyDB(
        provider=payload.provider,
        api_key=payload.api_key,
        label=payload.label,
        token_limit=payload.token_limit,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    logger.info(f"Added API key ID {key.id} for provider '{key.provider}'")
    return key


@router.get("/", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    _user: UserDB = Depends(get_current_user)
):
    """List all stored API keys. The actual key value is never returned."""
    result = await db.execute(select(APIKeyDB))
    return result.scalars().all()


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: int, 
    payload: APIKeyUpdate, 
    db: AsyncSession = Depends(get_db),
    _user: UserDB = Depends(admin_required)
):
    """Update is_active, token_limit, or label for an existing key."""
    result = await db.execute(select(APIKeyDB).where(APIKeyDB.id == key_id))
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail=f"API key ID {key_id} not found")

    if payload.is_active is not None:
        key.is_active = payload.is_active
    if payload.token_limit is not None:
        key.token_limit = payload.token_limit
    if payload.label is not None:
        key.label = payload.label

    await db.commit()
    await db.refresh(key)
    return key


@router.delete("/{key_id}", status_code=204)
async def delete_api_key(
    key_id: int, 
    db: AsyncSession = Depends(get_db),
    _user: UserDB = Depends(admin_required)
):
    """Permanently delete an API key."""
    result = await db.execute(select(APIKeyDB).where(APIKeyDB.id == key_id))
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail=f"API key ID {key_id} not found")

    await db.delete(key)
    await db.commit()
    logger.info(f"Deleted API key ID {key_id}")
