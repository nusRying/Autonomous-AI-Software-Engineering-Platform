"""
Configuration management using Pydantic Settings.
All values are loaded from environment variables or .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Autonomous Audit Platform"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./audit_platform.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    use_temporal: bool = True

    # LLM Defaults
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"

    # API Keys (optional — can also be added via /api/api_keys endpoint)
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Docker sandbox limits
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_quota: int = 50000
    sandbox_timeout_seconds: int = 60

    # Output
    audit_output_dir: str = "./audit_reports"

    # Security
    secret_key: str = "super-secret-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 # 24 hours
    dashboard_webhook_secret: str = "appsmith-default-secret-change-me"

    # MinIO
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "audit-reports"
    minio_region: str = "us-east-1"
    use_minio: bool = True


# Single shared instance imported across the app
settings = Settings()
