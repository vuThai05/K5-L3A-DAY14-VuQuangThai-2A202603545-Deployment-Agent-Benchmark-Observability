"""Redis-backed, atomic sliding-window rate limiter."""

import hashlib
import math
import secrets
import time

import redis
from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local cutoff = tonumber(ARGV[2])
local member = ARGV[3]
local limit = tonumber(ARGV[4])
local window_ms = tonumber(ARGV[5])
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry_ms = window_ms
  if oldest[2] then retry_ms = math.max(1, tonumber(oldest[2]) + window_ms - now) end
  return {0, retry_ms}
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, math.ceil(window_ms / 1000) + 1)
return {1, 0}
"""


def check_rate_limit(key: str) -> None:
    """Allow at most the configured number of requests in the last 60 seconds."""
    now_ms = time.time_ns() // 1_000_000
    window_ms = 60_000
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    redis_key = f"rate-limit:{key_hash}"
    member = f"{now_ms}:{secrets.token_hex(8)}"
    try:
        allowed, retry_ms = r.eval(
            _SLIDING_WINDOW,
            1,
            redis_key,
            now_ms,
            now_ms - window_ms,
            member,
            settings.rate_limit_per_minute,
            window_ms,
        )
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Rate limiter unavailable") from exc

    if int(allowed) != 1:
        retry_after = max(1, math.ceil(int(retry_ms) / 1000))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
