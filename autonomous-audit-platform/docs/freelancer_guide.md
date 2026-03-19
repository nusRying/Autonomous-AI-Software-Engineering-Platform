# System Description for Freelancers

Welcome to the **Autonomous Audit Platform**. This project uses a comprehensive development and management system based on self-hosted **GitLab Community Edition (CE)**, designed so that any collaborator can view, understand, and contribute safely and efficiently.

## Core Principles

1.  **Total Visibility**: The "Project X-Ray" (powered by Backstage and TechDocs) provides a full "Radiografía" of the project architecture, services, and APIs.
2.  **Autonomous Engineering**: Agents can autonomously propose changes, scan for vulnerabilities, and generate documentation.
3.  **The Safety Valve**: While agents can propose updates, **changes are only applied by authorized personnel** (Maintainer / Owner). This ensures human-in-the-loop oversight for all critical operations.
4.  **Full Audit Trail**: All changes, installations, and configurations are **tracked** via Temporal workflows and logged in the system state, ensuring 100% transparency and reproducibility.

## Collaborative Workflow

1.  **Explore**: Use the Backstage Catalog and System Diagrams to understand the architecture.
2.  **Propose**: Use the Appsmith Dashboard to trigger an Engineering Agent to create a Merge Request in GitLab.
3.  **Review**: The Maintainer reviews the agent-generated PR in GitLab.
4.  **Execute**: Upon approval, the Maintainer triggers the deployment workflow from the dashboard, which uses Ansible and Docker to apply the changes.

This hybrid approach combines the speed of AI automation with the security and oversight of traditional engineering practices.
