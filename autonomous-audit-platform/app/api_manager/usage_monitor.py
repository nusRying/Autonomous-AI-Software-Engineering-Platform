"""
Usage monitor: tracks token consumption per API key.
After each LLM call, call record_usage() to increment token count.
If the key exceeds its limit, it's automatically disabled.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.db.models import APIKeyDB, APIUsageDB


# Rough cost estimates ($ per 1M tokens) - generic fallbacks
COST_MAP = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 2.50, "out": 10.00},
    "claude-3-5-sonnet-latest": {"in": 3.00, "out": 15.00},
    "claude-3-haiku-20240307": {"in": 0.25, "out": 1.25},
}


async def record_usage(
    db: AsyncSession, 
    key_id: int, 
    model: str, 
    tokens_in: int, 
    tokens_out: int
) -> bool:
    """
    Increment token count for a key and log to APIUsageDB.
    Returns True if key is still active, False if now deactivated.
    """
    result = await db.execute(select(APIKeyDB).where(APIKeyDB.id == key_id))
    key = result.scalar_one_or_none()

    if not key:
        logger.warning(f"API key ID {key_id} not found — cannot record usage")
        return False

    # Calculate estimated cost
    model_costs = COST_MAP.get(model, {"in": 0.5, "out": 1.5}) # fallback
    est_cost = (tokens_in * model_costs["in"] / 1_000_000) + (tokens_out * model_costs["out"] / 1_000_000)

    # 1. Update the key's running counts
    total_tokens = tokens_in + tokens_out
    key.tokens_used += total_tokens
    key.total_usage_cost += est_cost

    # 2. Log detailed usage entry
    usage_log = APIUsageDB(
        key_id=key_id,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=est_cost
    )
    db.add(usage_log)

    # 3. Handle rotation threshold
    if key.tokens_used >= key.token_limit:
        key.is_active = False
        logger.warning(
            f"API key ID {key_id} ({key.provider}) deactivated — hit {key.tokens_used} limit"
        )
    
    await db.commit()
    return key.is_active


async def disable_key_temporarily(
    db: AsyncSession,
    key_id: int,
    seconds: int = 3600
) -> None:
    """
    Mark a key as disabled until a certain time (cool-down).
    Defaults to 1 hour.
    """
    from datetime import datetime, timedelta, timezone
    
    result = await db.execute(select(APIKeyDB).where(APIKeyDB.id == key_id))
    key = result.scalar_one_or_none()
    
    if key:
        key.disabled_until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        logger.info(f"API key ID {key_id} put on cool-down for {seconds}s (until {key.disabled_until})")
        await db.commit()


async def get_active_keys(db: AsyncSession, provider: str) -> list[APIKeyDB]:
    """Fetch all active keys for a given provider, ordered by tokens used (least first)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    result = await db.execute(
        select(APIKeyDB)
        .where(
            APIKeyDB.provider == provider, 
            APIKeyDB.is_active == True,
            (APIKeyDB.disabled_until == None) | (APIKeyDB.disabled_until <= now)
        )
        .order_by(APIKeyDB.tokens_used.asc())
    )
    return result.scalars().all()
