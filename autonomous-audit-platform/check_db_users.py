import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.db.models import UserDB

async def check_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserDB))
        users = result.scalars().all()
        print(f"Total users: {len(users)}")
        for u in users:
            print(f"User: {u.username}, Role: {u.role}, Email: {u.email}")

if __name__ == "__main__":
    asyncio.run(check_users())
