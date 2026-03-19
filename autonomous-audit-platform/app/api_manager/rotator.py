"""
LiteLLM-powered API key rotator.

How it works:
1. A caller asks for an LLM completion via call_llm()
2. Rotator picks the first active key for the provider
3. Makes the call via LiteLLM (which works with any provider)
4. Records token usage after success
5. If the key is rate-limited or exhausted, automatically tries the next one

Why LiteLLM?
- One unified interface for OpenAI, Anthropic, Ollama, Cohere, etc.
- No need to write separate adapters for each provider
"""
import litellm
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import APIKeyDB
from app.api_manager.usage_monitor import get_active_keys, record_usage
from app.config import settings


async def call_llm(
    db: AsyncSession,
    messages: list[dict],
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """
    Make an LLM call with automatic key rotation on failure.

    Args:
        db: Database session (for reading/updating keys)
        messages: List of {"role": "...", "content": "..."} dicts
        provider: e.g. "openai", "anthropic" — defaults to settings value
        model: e.g. "gpt-4o-mini" — defaults to settings value

    Returns:
        The LLM response text

    Raises:
        RuntimeError: If all active keys are exhausted
    """
    provider = provider or settings.default_llm_provider
    model = model or settings.default_llm_model

    active_keys = await get_active_keys(db, provider)

    # If no keys in DB, fall back to environment variable keys
    if not active_keys:
        logger.warning(f"No DB keys for provider '{provider}' — using env key")
        response = await litellm.acompletion(model=model, messages=messages)
        return response.choices[0].message.content

    # Try each key in order (keys are sorted: least used first)
    for key in active_keys:
        try:
            # Pass the key directly to facilitate thread-safety in async environments
            response = await litellm.acompletion(
                model=model, 
                messages=messages,
                api_key=key.api_key
            )

            # Count tokens used and update DB
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            
            await record_usage(db, key.id, model, prompt_tokens, completion_tokens)

            logger.info(f"LLM call succeeded via key ID {key.id} ({key.provider}), {prompt_tokens + completion_tokens} tokens")
            return response.choices[0].message.content

        except (litellm.RateLimitError, litellm.ContextWindowExceededError):
            logger.warning(f"Limit reached (Rate/Context) on key ID {key.id} — putting on cool-down")
            # Disable key for 10 minutes (600s) for rate limit
            from app.api_manager.usage_monitor import disable_key_temporarily
            await disable_key_temporarily(db, key.id, seconds=600)
            continue

        except litellm.AuthenticationError:
            logger.error(f"Authentication failed for key ID {key.id} — deactivating permanently")
            await record_usage(db, key.id, model, key.token_limit, 0)
            continue

        except Exception as e:
            logger.error(f"Error with key ID {key.id}: {e}")
            # Temporary disable for 5 mins for unknown errors
            from app.api_manager.usage_monitor import disable_key_temporarily
            await disable_key_temporarily(db, key.id, seconds=300)
            continue

    raise RuntimeError(
        f"All active API keys for provider '{provider}' are exhausted or failed. "
        "Please add more keys via POST /api/api_keys"
    )
