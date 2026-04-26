from typing import Optional
from src.config import CacheConfig
from src.services.cache.base_cache import BaseCache, K, V
from src.services.cache.cachetools_cache import CachetoolsCache

class CacheService(BaseCache[K, V]):
    """Cache service that delegates to a concrete cache implementation based on config."""

    def __init__(self, config: CacheConfig):
        self._impl = self._create_impl(config.cache_type, config.max_size, config.ttl)

    @staticmethod
    def _create_impl(cache_type: str, maxsize: int, ttl: int) -> BaseCache:
        if cache_type == "cachetools":
            return CachetoolsCache(maxsize=maxsize, ttl=ttl)
        raise ValueError(f"Unsupported cache type: {cache_type}")

    def get(self, key: K) -> Optional[V]:
        return self._impl.get(key)

    def set(self, key: K, value: V) -> None:
        self._impl.set(key, value)

    def delete(self, key: K) -> None:
        self._impl.delete(key)

    def contains(self, key: K) -> bool:
        return self._impl.contains(key)

    def clear(self) -> None:
        self._impl.clear()
