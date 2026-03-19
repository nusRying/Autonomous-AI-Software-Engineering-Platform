import asyncio
from app.database import init_db
from app.main import init_admin

async def main():
    print("Initializing database...")
    await init_db()
    print("Database initialized.")
    print("Creating default admin...")
    await init_admin()
    print("Default admin check complete.")

if __name__ == "__main__":
    asyncio.run(main())
