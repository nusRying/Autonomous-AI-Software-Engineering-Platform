"""Health check route."""
from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check():
    """Returns app status and version. Use this to verify the server is running."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "app": settings.app_name,
    }
