"""
Database engine and session management.
Using SQLAlchemy 2.0 async with aiosqlite for SQLite.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a DB session, closes it after request."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables on startup."""
    from app.db.models import Base # Register models from models.py
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
