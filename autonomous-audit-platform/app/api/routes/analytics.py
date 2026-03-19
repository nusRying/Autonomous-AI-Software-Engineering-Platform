from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String
from typing import List

from app.database import get_db
from app.db.models import APIUsageDB, APIKeyDB
from app.models.analytics import UsageStatsResponse, DailyUsage, ProviderUsage

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(db: AsyncSession = Depends(get_db)):
    """Fetch aggregated usage statistics for the dashboard charts."""
    
    # 1. Total tokens
    total_res = await db.execute(select(func.sum(APIUsageDB.tokens_in + APIUsageDB.tokens_out)))
    total_tokens = total_res.scalar() or 0
    
    # 2. Daily usage (last 7 days)
    daily_res = await db.execute(
        select(
            func.date(APIUsageDB.timestamp, type_=String).label("day"),
            func.sum(APIUsageDB.tokens_in + APIUsageDB.tokens_out).label("tokens")
        )
        .group_by("day")
        .order_by("day")
        .limit(7)
    )
    daily_usage = [DailyUsage(day=row.day, tokens=row.tokens) for row in daily_res]
    
    # 3. Provider breakdown
    provider_res = await db.execute(
        select(
            APIKeyDB.provider,
            func.sum(APIUsageDB.tokens_in + APIUsageDB.tokens_out).label("tokens")
        )
        .join(APIKeyDB, APIKeyDB.id == APIUsageDB.key_id)
        .group_by(APIKeyDB.provider)
    )
    provider_usage = [ProviderUsage(provider=row.provider, tokens=row.tokens) for row in provider_res]
    
    return UsageStatsResponse(
        total_tokens=total_tokens,
        daily_usage=daily_usage,
        provider_usage=provider_usage
    )
