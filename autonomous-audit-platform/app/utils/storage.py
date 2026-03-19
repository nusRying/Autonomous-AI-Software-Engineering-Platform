"""
Async storage utility for MinIO / S3.
"""
import aioboto3
from loguru import logger
from app.config import settings
from typing import Optional

class StorageClient:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint = settings.minio_endpoint
        self.access_key = settings.minio_access_key
        self.secret_key = settings.minio_secret_key
        self.bucket = settings.minio_bucket
        self.region = settings.minio_region

    async def get_client(self):
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

    async def ensure_bucket_exists(self):
        """Create the bucket if it doesn't exist."""
        async with await self.get_client() as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket)
                logger.debug(f"MinIO bucket '{self.bucket}' exists.")
            except Exception:
                logger.info(f"Creating MinIO bucket '{self.bucket}'...")
                await s3.create_bucket(Bucket=self.bucket)

    async def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload raw bytes to MinIO."""
        async with await self.get_client() as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            logger.info(f"Uploaded to MinIO: {key}")
            return f"{self.endpoint}/{self.bucket}/{key}"

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned GET URL for a file."""
        async with await self.get_client() as s3:
            try:
                url = await s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': key},
                    ExpiresIn=expires_in
                )
                return url
            except Exception as e:
                logger.error(f"Failed to generate presigned URL for {key}: {e}")
                return None

    async def list_objects(self, prefix: str = ""):
        """List objects in the bucket with a given prefix."""
        async with await self.get_client() as s3:
            response = await s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return response.get('Contents', [])

    async def download_bytes(self, key: str) -> bytes:
        """Download an object from MinIO as bytes."""
        async with await self.get_client() as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=key)
            async with response['Body'] as stream:
                return await stream.read()

# Singleton instance
storage_client = StorageClient()
