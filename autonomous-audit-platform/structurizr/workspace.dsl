workspace "Autonomous Audit Platform" "Architecture Baseline" {

    model {
        user = person "Security Engineer" "A user who performs audits and manages API keys."
        
        softwareSystem = softwareSystem "Autonomous Audit Platform" "Enables automated software audits and AI-driven engineering tasks." {
            apiApp = container "Orchestrator API (Monolith)" "FastAPI application providing the core logic and endpoints." "Python/FastAPI"
            db = container "Database" "Stores user data, API keys, and audit results." "PostgreSQL"
            storage = container "MinIO / S3" "Stores audit reports and raw artifacts." "Object Storage"
            temporal = container "Temporal" "Orchestrates long-running workflows and agent tasks." "Go/Temporal"
            
            auditAgent = container "Audit Agent Service" "Specialized AI agent for code analysis and infrastructure auditing." "Python"
            engineeringAgent = container "Engineering Agent Service" "Specialized AI agent for code generation, vision, and crawling." "Python"
            
            dashboard = container "Interactive Dashboard" "Low-code interface for system monitoring and human-in-the-loop actions." "Appsmith"
        }

        user -> softwareSystem "Uses"
        user -> dashboard "Interacts with"
        
        dashboard -> apiApp "Requests State / Proposes Changes" "HTTPS/JSON"
        apiApp -> db "Reads/Writes" "SQL"
        apiApp -> temporal "Triggers Workflows" "gRPC"
        temporal -> auditAgent "Executes Audit Tasks" "Activity"
        temporal -> engineeringAgent "Executes Engineering Tasks" "Activity"
        
        auditAgent -> storage "Persists Reports" "S3 API"
        engineeringAgent -> storage "Persists Artifacts" "S3 API"
        
        apiApp -> storage "Reads Reports/Artifacts" "S3 API"
    }

    views {
        systemContext softwareSystem "Context" {
            include *
            autoLayout
        }

        container softwareSystem "Containers" {
            include *
            autoLayout
        }

        theme default
    }

}
