from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional

K = TypeVar("K")
V = TypeVar("V")

class BaseCache(ABC, Generic[K, V]):

    @abstractmethod
    def get(self, key: K) -> Optional[V]:
        ...

    @abstractmethod
    def set(self, key: K, value: V) -> None:
        ...

    @abstractmethod
    def delete(self, key: K) -> None:
        ...

    @abstractmethod
    def contains(self, key: K) -> bool:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...
