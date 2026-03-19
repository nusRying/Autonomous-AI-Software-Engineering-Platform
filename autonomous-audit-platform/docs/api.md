# API Guide

The Autonomous Audit Platform provides a RESTful API for interacting with the orchestrator and agents.

## OpenAPI Documentation
The interactive API documentation is available at `/docs` (Swagger UI) or `/redoc` (ReDoc) when the server is running.

## Authentication
The API uses JWT-based authentication. Users must log in to get an access token.

## Main Endpoints
- `/api/auth`: User authentication and token management.
- `/api/api_keys`: Management of LLM provider API keys.
- `/api/audit`: Endpoints for starting and managing software audits.
- `/api/engineer`: Endpoints for triggering engineering tasks.
- `/api/analytics`: Usage and performance metrics.
- `/dashboard`: Integration endpoints for Appsmith.

## Backstage Integration
The API specification is automatically ingested into the Backstage catalog as an `API` entity.
