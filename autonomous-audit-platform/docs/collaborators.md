# Collaborator Guide

This project uses a comprehensive development and management system based on self-hosted **GitLab Community Edition (CE)**, designed so that any collaborator can view, understand, and contribute safely and efficiently.

## Core Principles

*   **Full Architecture Visibility**: Through the "Project X-Ray" layer, every collaborator has access to real-time system diagrams, service catalogs, and API specifications.
*   **Traceable Operations**: All changes, installations, and configurations are **traceable**. Every action taken by an AI agent or a human is recorded in Temporal workflows and GitLab audit logs.
*   **Controlled Deployment**: To maintain system integrity, changes are only applied by authorized personnel (**Maintainers/Owners**). Collaborators propose; owners authorize.
*   **Automation & Reproducibility**: Every module installation and update is handled via automated CI/CD pipelines (Ansible + Docker), ensuring that the environment is always reproducible.

## The Contribution Flow
1.  **Analyze**: Use Backstage to understand the impact of a proposed change.
2.  **Propose**: Submit a proposal via the Appsmith Dashboard.
3.  **Review**: An Engineering Agent creates a Merge Request in GitLab for peer review.
4.  **Execute**: Once the Maintainer approves, the "Safety Valve" triggers the automated deployment.
