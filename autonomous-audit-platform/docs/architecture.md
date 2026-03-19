# System Architecture

The Autonomous Audit Platform is a multi-agent system designed for automated software engineering tasks.

## C4 Model
The platform's architecture follows the C4 model for software architecture visualization.

### Containers
1. **Orchestrator API (Monolith)**: The central FastAPI application that provides the core logic and manages the REST API.
2. **Audit Agent Service**: Specialized AI agents that perform code analysis and security auditing.
3. **Engineering Agent Service**: Specialized AI agents that generate code, process visual data, and crawl the web.
4. **Interactive Dashboard**: A human-in-the-loop dashboard powered by Appsmith for monitoring and high-level control.
5. **Database**: A PostgreSQL database for storing user data, API keys, and audit results.
6. **Temporal Cluster**: The workflow engine that coordinates distributed tasks and long-running processes.
7. **MinIO Storage**: S3-compatible object storage for persisting audit reports and artifacts.

## Agent Orchestration
Agents are triggered by the Orchestrator via Temporal workflows. This allows for distributed execution and resilient task management.
