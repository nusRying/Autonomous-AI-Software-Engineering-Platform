"""
Rigorous LLM Rotation and Failover tests.
Mocks litellm if not installed.
"""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock litellm before it's imported by app code
if "litellm" not in sys.modules:
    mock_litellm = MagicMock()
    # Define exception classes
    class RateLimitError(Exception): pass
    class ContextWindowExceededError(Exception): pass
    class AuthenticationError(Exception): pass
    
    mock_litellm.RateLimitError = RateLimitError
    mock_litellm.ContextWindowExceededError = ContextWindowExceededError
    mock_litellm.AuthenticationError = AuthenticationError
    sys.modules["litellm"] = mock_litellm

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api_manager.rotator import call_llm
from app.db.models import APIKeyDB
import litellm # Now this is our mock

@pytest.mark.anyio
async def test_llm_rotation_on_rate_limit(db: AsyncSession):
    """Verify that a RateLimitError on the first key triggers failover to the second key."""
    
    # 1. Setup two test keys in DB
    key1 = APIKeyDB(provider="openai", api_key="sk-rate-limited", label="Key 1", is_active=True)
    key2 = APIKeyDB(provider="openai", api_key="sk-working", label="Key 2", is_active=True)
    db.add_all([key1, key2])
    await db.commit()

    # 2. Setup mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Success from key 2"))]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

    # 3. Configure mock side effect
    litellm.acompletion = AsyncMock(side_effect=[
        litellm.RateLimitError("Rate limit reached"),
        mock_response
    ])

    # 4. Call LLM
    result = await call_llm(db, [{"role": "user", "content": "test"}], provider="openai")

    # 5. Assertions
    assert result == "Success from key 2"
    assert litellm.acompletion.call_count == 2
    
    # Verify key1 was temporarily disabled
    # Force fresh fetch from DB
    result = await db.execute(select(APIKeyDB).where(APIKeyDB.id == 1))
    db_key1 = result.scalar_one()
    assert db_key1.disabled_until is not None

@pytest.mark.anyio
async def test_llm_deactivation_on_auth_error(db: AsyncSession):
    """Verify that an AuthenticationError exhausts the key."""
    
    # 1. Setup a bad key
    key = APIKeyDB(provider="openai", api_key="sk-invalid", label="Bad Key", is_active=True, token_limit=1000, tokens_used=0)
    db.add(key)
    await db.commit()

    # 2. Setup mock side effect
    litellm.acompletion = AsyncMock(side_effect=litellm.AuthenticationError("Invalid API Key"))

    # 3. Call LLM
    with pytest.raises(RuntimeError) as exc:
        await call_llm(db, [{"role": "user", "content": "test"}], provider="openai")
    
    assert "exhausted" in str(exc.value)

    # 4. Verify key is effectively disabled
    db.expire_all()
    result = await db.execute(select(APIKeyDB).where(APIKeyDB.api_key == "sk-invalid"))
    db_key = result.scalar_one()
    assert db_key.tokens_used >= db_key.token_limit
