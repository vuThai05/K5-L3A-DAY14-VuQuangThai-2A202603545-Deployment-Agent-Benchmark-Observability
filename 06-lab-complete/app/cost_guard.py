"""Daily per-API-key budget guard, persisted in Redis."""

import hashlib
from contextvars import ContextVar, Token
from datetime import datetime, timedelta, timezone

import redis
from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006
_current_api_key: ContextVar[str] = ContextVar("cost_guard_api_key", default="")


def set_current_api_key(key: str) -> Token:
    return _current_api_key.set(key)


def reset_current_api_key(token: Token) -> None:
    _current_api_key.reset(token)


def _budget_key() -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"daily-cost:{day}"


def _caller_key() -> str:
    """Hash the API key so Redis never stores a credential in a key name."""
    return hashlib.sha256(_current_api_key.get().encode("utf-8")).hexdigest()


def check_budget(estimated_cost_usd: float = 0.0) -> None:
    """Reject a request when its estimated cost would exceed the daily budget."""
    try:
        spent = float(r.hget(_budget_key(), _caller_key()) or 0.0)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Cost guard unavailable") from exc
    if spent + max(0.0, estimated_cost_usd) > settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Persist estimated token cost and return the current day's total."""
    cost = (
        max(0, input_tokens) / 1000 * PRICE_INPUT_PER_1K
        + max(0, output_tokens) / 1000 * PRICE_OUTPUT_PER_1K
    )
    key = _budget_key()
    field = _caller_key()
    try:
        total = float(r.hincrbyfloat(key, field, cost))
        now = datetime.now(timezone.utc)
        midnight_tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        r.expire(key, max(1, int((midnight_tomorrow - now).total_seconds()) + 60))
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Cost guard unavailable") from exc
    return total
