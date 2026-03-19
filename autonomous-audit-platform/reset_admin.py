import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.db.models import UserDB
from app.utils.security import get_password_hash

async def reset_admin():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserDB).where(UserDB.username == "admin"))
        user = result.scalar_one_or_none()
        if user:
            user.hashed_password = get_password_hash("admin123")
            await db.commit()
            print("Admin password reset to 'admin123'")
        else:
            print("Admin user not found")

if __name__ == "__main__":
    asyncio.run(reset_admin())
