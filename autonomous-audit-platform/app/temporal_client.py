"""
Temporal client for workflow orchestration.
"""
from temporalio.client import Client
from app.config import settings
from loguru import logger

async def get_temporal_client() -> Client:
    try:
        client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace
        )
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Temporal: {e}")
        raise
