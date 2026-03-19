import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.db.models import Base, UserDB, APIKeyDB, APIUsageDB, AuditJobDB
from app.database import get_db
from app.main import app

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Tables are created once per session
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db(test_engine):
    """Provide a clean database session for each test."""
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with TestSessionLocal() as session:
        yield session
        # Cleanup: we could delete all data here if we wanted to be very clean
        # but for in-memory it doesn't matter much between tests if they don't collide
        await session.rollback()

@pytest.fixture(autouse=True)
async def override_get_db(db):
    """Override the FastAPI dependency with the test database session."""
    async def _get_test_db():
        yield db
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture(autouse=True)
async def mock_lifespan(monkeypatch):
    """Mock init_db and init_admin to avoid collision with test DB setup."""
    from app import main
    async def dummy_init(): pass
    monkeypatch.setattr(main, "init_db", dummy_init)
    monkeypatch.setattr(main, "init_admin", dummy_init)
