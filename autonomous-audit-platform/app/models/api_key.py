"""
Pydantic models for API key management.
These define the shape of data going IN and OUT of the /api/api_keys endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class APIKeyCreate(BaseModel):
    """Data required to add a new API key."""
    provider: str = Field(..., examples=["openai", "anthropic", "cohere"])
    api_key: str = Field(..., min_length=10)
    token_limit: int = Field(default=100_000, description="Max tokens before auto-rotation")
    label: Optional[str] = Field(None, description="Optional human-readable label")


class APIKeyResponse(BaseModel):
    """What we return when listing API keys (never expose the actual key)."""
    id: int
    provider: str
    label: Optional[str]
    is_active: bool
    token_limit: Optional[int] = None
    tokens_used: int
    disabled_until: Optional[datetime] = None

    model_config = {"from_attributes": True}


class APIKeyUpdate(BaseModel):
    """Fields allowed to update on an existing key."""
    is_active: Optional[bool] = None
    token_limit: Optional[int] = None
    label: Optional[str] = None
