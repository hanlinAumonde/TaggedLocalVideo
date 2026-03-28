from typing import Optional
from cachetools import TTLCache
from src.services.cache.base_cache import BaseCache, K, V

class CachetoolsCache(BaseCache[K, V]):

    def __init__(self, maxsize: int, ttl: int):
        self._cache: TTLCache[K, V] = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: K) -> Optional[V]:
        return self._cache.get(key)

    def set(self, key: K, value: V) -> None:
        self._cache[key] = value

    def delete(self, key: K) -> None:
        self._cache.pop(key, None)

    def contains(self, key: K) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()
