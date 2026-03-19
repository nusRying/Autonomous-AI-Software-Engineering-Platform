"""
Pydantic models for audit request and response.
These define the data shapes for POST /audit and GET /audit/{job_id}.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class AuditStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditRequest(BaseModel):
    """User submits either a local path or a git URL."""
    repo_path: Optional[str] = Field(None, description="Absolute path to a local repo")
    repo_url: Optional[str] = Field(None, description="Git URL to clone and audit")
    run_tests: bool = Field(False, description="Run pytest inside Docker sandbox")


class DocAnalysis(BaseModel):
    frameworks: List[str] = []
    architecture_summary: str = ""
    requirements: List[str] = []


class CodeScanResult(BaseModel):
    language: str = "unknown"
    dependencies: List[str] = []
    issues: List[str] = []
    has_dockerfile: bool = False
    has_requirements: bool = False
    file_count: int = 0


class RuntimeError_(BaseModel):
    error_type: str
    message: str
    severity: str  # critical | warning | info


class DockerResult(BaseModel):
    build_success: bool = False
    run_success: bool = False
    exit_code: Optional[int] = None
    logs: str = ""


class AuditReport(BaseModel):
    job_id: str
    repo_path: str
    status: AuditStatus
    doc_analysis: Optional[DocAnalysis] = None
    code_scan: Optional[CodeScanResult] = None
    docker_result: Optional[DockerResult] = None
    runtime_errors: List[RuntimeError_] = []
    recommendations: List[str] = []
    summary: str = ""
    report_path: Optional[str] = None
    error_message: Optional[str] = None
