import asyncio
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import bcrypt

# The actual DB used by the app according to .env and config.py
DATABASE_URL = "sqlite+aiosqlite:///./audit_platform.db"

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

async def reset_admin():
    from app.db.models import Base, UserDB
    
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserDB).where(UserDB.username == "admin"))
        user = result.scalar_one_or_none()
        if user:
            user.hashed_password = get_password_hash("admin123")
            user.email = "admin@audit.platform" # Ensure valid email
            await db.commit()
            print("SUCCESS: Admin password reset to 'admin123' in ./audit_platform.db")
        else:
            print("ERROR: Admin user not found in ./audit_platform.db")

if __name__ == "__main__":
    # Ensure we are in the right directory or use absolute path
    asyncio.run(reset_admin())
