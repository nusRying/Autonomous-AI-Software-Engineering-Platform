import asyncio
from app.config import settings
from app.utils.storage import storage_client

async def check():
    job_id = "b29cb92b-2f45-4290-a0c5-a67c315d8b6f"
    prefix = f"{job_id}/"
    print(f"Checking prefix: {prefix}")
    try:
        if not settings.use_minio:
            print("MinIO is disabled in settings.")
            return
            
        objects = await storage_client.list_objects(prefix)
        print(f"Found objects: {[obj.get('Key') for obj in objects]}")
        
        md_key = f"{job_id}/report.md"
        if any(obj.get('Key') == md_key for obj in objects):
            content = await storage_client.download_bytes(md_key)
            print(f"MD content length: {len(content)}")
            print("First 100 chars:", content[:100].decode('utf-8', errors='ignore'))
        else:
            print(f"File {md_key} not found in listing.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
