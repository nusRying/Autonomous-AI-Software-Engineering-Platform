import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.db.models import UserDB

async def fix_email():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserDB).where(UserDB.username == "admin"))
        user = result.scalar_one_or_none()
        if user:
            user.email = "admin@audit.platform"
            await db.commit()
            print("Admin email updated to 'admin@audit.platform'")
        else:
            print("Admin user not found")

if __name__ == "__main__":
    asyncio.run(fix_email())
