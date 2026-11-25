"""Environment-based settings for the production agent."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int
    environment: str
    agent_api_key: str
    redis_url: str
    rate_limit_per_minute: int
    daily_budget_usd: float


settings = Settings(
    port=int(os.getenv("PORT", "8000")),
    environment=os.getenv("ENVIRONMENT", "development"),
    agent_api_key=os.getenv("AGENT_API_KEY", ""),
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    rate_limit_per_minute=max(1, int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))),
    daily_budget_usd=max(0.0, float(os.getenv("DAILY_BUDGET_USD", "1.0"))),
)
