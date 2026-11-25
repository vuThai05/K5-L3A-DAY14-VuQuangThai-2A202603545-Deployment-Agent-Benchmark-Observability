"""Lazy Redis client; importing the app never requires a live Redis server."""

import redis

from app.config import settings

r = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=1.0,
    health_check_interval=30,
)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except redis.RedisError:
        return False
