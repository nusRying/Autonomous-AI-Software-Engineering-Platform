import asyncio
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import bcrypt

# Ensure we use the exact same DB and logic as the app
DATABASE_URL = "sqlite+aiosqlite:///./audit_platform.db"

async def test_login():
    from app.db.models import UserDB
    
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    username = "admin"
    password = "admin123"
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserDB).where(UserDB.username == username))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"FAILED: User {username} not found in DB")
            return

        # Check password hash logic
        is_valid = bcrypt.checkpw(password.encode("utf-8"), user.hashed_password.encode("utf-8"))
        
        print(f"User: {user.username}")
        print(f"Email: {user.email}")
        print(f"Hashed PW: {user.hashed_password}")
        print(f"Verification Result: {is_valid}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(test_login())
