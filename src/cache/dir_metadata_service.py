from functools import lru_cache
from pymongo import UpdateOne
from src.cache.cache_service import get_cache_service, CacheService
from src.db.models.DirMetadata_model import DirMetadataModel
from src.logger import get_logger

logger = get_logger("dir_metadata_service")


class DirMetadataService:

    def __init__(self):
        self._cache: CacheService = get_cache_service()

    async def get_metadata(self, path: str) -> tuple[float, float] | None:
        """Cache-Aside read: cache -> database -> None"""
        cached = self._cache.get(path)
        if cached is not None:
            return cached

        doc = await DirMetadataModel.find_one(DirMetadataModel.path == path)
        if doc is not None:
            result = (doc.total_size, doc.last_modified_time)
            self._cache.set(path, result)
            return result

        return None

    async def set_metadata(self, path: str, total_size: float, last_modified_time: float) -> None:
        """Single upsert to database + update cache."""
        await DirMetadataModel.get_pymongo_collection().update_one(
            {"path": path},
            {"$set": {
                "path": path,
                "total_size": total_size,
                "last_modified_time": last_modified_time,
            }},
            upsert=True
        )
        self._cache.set(path, (total_size, last_modified_time))

    async def bulk_set_metadata(self, entries: dict[str, tuple[float, float]]) -> None:
        """Bulk upsert to database, then batch update cache."""
        if not entries:
            return

        operations = [
            UpdateOne(
                {"path": path},
                {"$set": {
                    "path": path,
                    "total_size": total_size,
                    "last_modified_time": last_modified_time,
                }},
                upsert=True
            )
            for path, (total_size, last_modified_time) in entries.items()
        ]

        try:
            await DirMetadataModel.get_pymongo_collection().bulk_write(operations)
        except Exception as e:
            logger.error(f"Bulk write error during dir metadata upsert: {e}")

        for path, value in entries.items():
            self._cache.set(path, value)


@lru_cache
def get_dir_metadata_service() -> DirMetadataService:
    return DirMetadataService()
