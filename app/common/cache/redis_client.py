from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis

from app.configs.settings import get_settings


@lru_cache
def get_redis_pool() -> redis.ConnectionPool:
    settings = get_settings()
    return redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    client = redis.Redis(connection_pool=get_redis_pool())
    try:
        yield client
    finally:
        await client.aclose()
