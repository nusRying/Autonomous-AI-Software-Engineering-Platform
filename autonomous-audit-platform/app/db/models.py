"""
Centralized SQLAlchemy ORM models for the Autonomous Audit Platform.
"""
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    OBSERVER = "observer"

class AuditStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class EngineerStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    CODING = "coding"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class UserDB(Base):
    """Database table: stores platform users and roles."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.OBSERVER)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    audit_jobs = relationship("AuditJobDB", back_populates="owner")
    engineer_jobs = relationship("EngineerJobDB", back_populates="owner")


class APIKeyDB(Base):
    """Database table: stores one row per API key."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False)          # e.g. "openai", "anthropic"
    api_key = Column(String, nullable=False)           # the actual secret key
    label = Column(String, nullable=True)              # optional human name
    is_active = Column(Boolean, default=True)          # False when limit is hit
    token_limit = Column(Integer, default=100_000)     # threshold for rotation
    tokens_used = Column(Integer, default=0)           # running token count
    total_usage_cost = Column(Float, default=0.0)      # total accrued cost ($)
    disabled_until = Column(DateTime(timezone=True), nullable=True) # for cool-down

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    usage_logs = relationship("APIUsageDB", back_populates="api_key_ref")


class APIUsageDB(Base):
    """Database table: tracks every LLM call made by every key."""
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    model = Column(String, nullable=False)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    api_key_ref = relationship("APIKeyDB", back_populates="usage_logs")


class AuditJobDB(Base):
    """Database table: stores audit jobs and their results."""
    __tablename__ = "audit_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    repo_path = Column(String, nullable=True)
    repo_url = Column(String, nullable=True)
    status = Column(Enum(AuditStatus), default=AuditStatus.PENDING)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    error = Column(Text, nullable=True)
    health_score = Column(Integer, nullable=True)
    report_json = Column(Text, nullable=True)   # stringified JSON report
    report_data = Column(JSON, nullable=True)   # parsed JSON for analytics
    report_path = Column(String, nullable=True) # path to MD report on disk

    # Relationships
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("UserDB", back_populates="audit_jobs")


class EngineerJobDB(Base):
    """Database table: stores autonomous project generation jobs."""
    __tablename__ = "engineer_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    project_name = Column(String, nullable=True)
    project_prompt = Column(Text, nullable=False)
    status = Column(Enum(EngineerStatus), default=EngineerStatus.PENDING)
    
    technical_spec = Column(JSON, nullable=True)
    generated_repo_path = Column(String, nullable=True) # local path to result
    minio_repo_zip_url = Column(String, nullable=True)  # cloud backup
    
    error = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("UserDB", back_populates="engineer_jobs")
