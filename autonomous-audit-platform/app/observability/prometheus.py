from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Metrics for Agent Performance
AGENT_TASK_TOTAL = Counter(
    "agent_task_total", 
    "Total number of tasks processed by agents",
    ["agent_role", "status"]
)

LLM_LATENCY = Histogram(
    "llm_latency_seconds",
    "Latency of LLM API calls",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

TOKEN_USAGE = Counter(
    "llm_tokens_total",
    "Total tokens consumed by LLMs",
    ["provider", "model", "type"] # type=prompt or completion
)

AGENT_HEALTH_SCORE = Gauge(
    "agent_health_score",
    "Real-time health score of the autonomous system",
    ["project_id"]
)

def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

class MetricsTracker:
    @staticmethod
    def track_task(role: str, success: bool):
        status = "success" if success else "failure"
        AGENT_TASK_TOTAL.labels(agent_role=role, status=status).inc()

    @staticmethod
    def track_llm(provider: str, model: str, latency: float, prompt_tokens: int, completion_tokens: int):
        LLM_LATENCY.labels(provider=provider, model=model).observe(latency)
        TOKEN_USAGE.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
        TOKEN_USAGE.labels(provider=provider, model=model, type="completion").inc(completion_tokens)

    @staticmethod
    def update_health(project_id: str, score: float):
        AGENT_HEALTH_SCORE.labels(project_id=project_id).set(score)
