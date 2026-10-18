import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.common.abstracts.cache_port import CachePort

logger = logging.getLogger(__name__)


class RedisCache(CachePort):
    """Implementation của CachePort dùng Redis. Redis lỗi ở BẤT KỲ lệnh nào -> log warning,
    trả None, caller coi như cache miss/no-op. Không bao giờ raise ra ngoài — cache luôn là
    optional, nguồn sự thật (Postgres) không được phép fail theo Redis.

    Service/store phụ thuộc CachePort (type hint), không phụ thuộc RedisCache cụ thể:
        class CachedSessionStore:
            def __init__(self, cache: CachePort) -> None:
                self._cache = cache

            async def find_by_id(self, id: str) -> ...:
                raw = await self._cache.get(_session_key(id))
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, key: str) -> str | None:
        return await self._call(self._redis.get, key)

    async def set_value(self, key: str, value: str, ex: int) -> None:
        await self._call(self._redis.set, key, value, ex=ex)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self._call(self._redis.delete, *keys)

    async def sadd(self, key: str, *values: str) -> None:
        await self._call(self._redis.sadd, key, *values)

    async def smembers(self, key: str) -> set[str]:
        return await self._call(self._redis.smembers, key) or set()

    async def scan_keys(self, match: str) -> list[str]:
        keys: list[str] = []
        try:
            async for key in self._redis.scan_iter(match=match):
                keys.append(key)
        except RedisError as exc:
            logger.warning("RedisCache.scan_keys failed, falling back: %s", exc)
            return []
        return keys

    async def _call(self, fn, *args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except RedisError as exc:
            logger.warning("RedisCache operation failed, falling back: %s", exc)
            return None
