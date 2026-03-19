from pydantic import BaseModel
from datetime import date
from typing import List

class DailyUsage(BaseModel):
    day: date
    tokens: int

class ProviderUsage(BaseModel):
    provider: str
    tokens: int

class UsageStatsResponse(BaseModel):
    total_tokens: int
    daily_usage: List[DailyUsage]
    provider_usage: List[ProviderUsage]
