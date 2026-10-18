from typing import Protocol


class CachePort(Protocol):
    """Port trung lập cho cache key-value. RedisCache implement port này; service/store
    phụ thuộc port, không phụ thuộc redis-py trực tiếp — đổi backend (in-memory cho test,
    Memcached...) không đụng domain logic. Mọi implementation phải tự fail-open khi lỗi
    (trả None/no-op), không bao giờ raise ra ngoài — cache luôn optional."""

    async def get(self, key: str) -> str | None: ...

    async def set_value(self, key: str, value: str, ex: int) -> None: ...

    async def delete(self, *keys: str) -> None: ...

    async def sadd(self, key: str, *values: str) -> None: ...

    async def smembers(self, key: str) -> set[str]: ...

    async def scan_keys(self, match: str) -> list[str]: ...
