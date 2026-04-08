from functools import lru_cache
from pymongo import UpdateOne
from src.services.cache.cache_service import get_cache_service, CacheService
from src.config import get_settings
from src.db.models.DirMetadata_model import DirMetadataModel
from src.logger import get_logger
from src.services.path_convert_service import AbsolutePath
from src.services.resource_handler.resource_handler_service import get_resource_handler_service

logger = get_logger("dir_metadata_service")


class DirMetadataService:

    def __init__(self):
        self.settings = get_settings()
        self.resourceHandlerService = get_resource_handler_service()
        self._cache: CacheService = get_cache_service()

    def _cache_key(self, category: str, path: str) -> str:
        return f"{category}:{path}"

    async def get_metadata(self, category: str, path: str) -> tuple[float, float] | None:
        """Cache-Aside read: cache -> database -> None"""
        cache_key = self._cache_key(category, path)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        doc = await DirMetadataModel.find_one(
            DirMetadataModel.category == category,
            DirMetadataModel.path == path
        )
        if doc is not None:
            result = (doc.total_size, doc.last_modified_time)
            self._cache.set(cache_key, result)
            return result

        return None

    async def set_metadata(self, category: str, path: str, total_size: float, last_modified_time: float) -> None:
        """Single upsert to database + update cache."""
        await DirMetadataModel.get_pymongo_collection().update_one(
            {"category": category, "path": path},
            {"$set": {
                "category": category,
                "path": path,
                "total_size": total_size,
                "last_modified_time": last_modified_time,
            }},
            upsert=True
        )
        self._cache.set(self._cache_key(category, path), (total_size, last_modified_time))

    async def bulk_set_metadata(self, category: str, entries: dict[str, tuple[float, float]]) -> None:
        """Bulk upsert to database, then batch update cache."""
        if not entries:
            return

        operations = [
            UpdateOne(
                {"category": category, "path": path},
                {"$set": {
                    "category": category,
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
            logger.exception(f"Bulk write error during dir metadata upsert: {e}")

        for path, value in entries.items():
            self._cache.set(self._cache_key(category, path), value)

    async def calculate_directory_metadata(self,
                                           directory_path: AbsolutePath,
                                           skipCache: bool = False,
                                           recursiveCalculation: bool = True) -> tuple[float, float]:
        category = directory_path.category
        if category is None:
            return (0.0, 0.0)

        db_path = directory_path.DB_format_path()
        if not skipCache:
            cached = await self.get_metadata(category, db_path)
            if cached is not None:
                return cached

        collected: dict[str, tuple[float, float]] = {}
        result = await self._calculate_directory_metadata_impl(
            directory_path, collected, recursiveCalculation
        )
        collected[db_path] = result
        await self.bulk_set_metadata(category, collected)
        return result

    async def _calculate_directory_metadata_impl(self,
                                           directory_path: AbsolutePath,
                                           collected: dict[str, tuple[float, float]],
                                           recursiveCalculation: bool) -> tuple[float, float]:
        total_size = 0.0
        last_modified_time = 0.0
        category = directory_path.category

        try:
            from src.services.resource_handler.resource_handler_service import get_resource_handler_service
            handler = get_resource_handler_service().get_handler(category)
            with handler.list_directory(directory_path.FS_format_path()) as entries:
                for entry in entries:
                    if entry.is_dir():
                        sub_path = AbsolutePath.from_existing_path(entry.path, category)
                        if recursiveCalculation:
                            dir_size, dir_mtime = await self._calculate_directory_metadata_impl(
                                sub_path, collected, recursiveCalculation
                            )
                        else:
                            dir_size, dir_mtime = await self.get_metadata(category, sub_path.DB_format_path()) or (0.0, 0.0)
                        collected[sub_path.DB_format_path()] = (dir_size, dir_mtime)
                        total_size += dir_size
                        last_modified_time = max(last_modified_time, dir_mtime)
                    elif entry.is_file() and handler.is_video_file(entry.name):
                        stat = entry.stat()
                        total_size += stat.size
                        last_modified_time = max(last_modified_time, stat.mtime)

        except (OSError, Exception):
            logger.exception(f"Error accessing directory {directory_path} to calculate size and last modified time.")
            total_size = -1.0
            last_modified_time = -1.0

        return total_size, last_modified_time

    async def batch_update_metadata_forward(self, category: str, dir_db_paths: list[str]) -> None:
        """collect all parent directories of the given paths, then batch update their metadata"""
        if not dir_db_paths:
            return

        handler = self.resourceHandlerService.get_handler(category)
        logical_roots = self.settings.get_all_logical_root_paths()

        all_paths: set[str] = set()
        for db_path in dir_db_paths:
            current = db_path
            while current not in all_paths:
                all_paths.add(current)
                if current in logical_roots:
                    break
                parent = handler.dirname(current)
                if not parent or parent == current:
                    break
                current = parent

        for db_path in sorted(all_paths, key=lambda p: p.count('/'), reverse=True):
            abs_path = AbsolutePath.from_existing_path(db_path, category)
            await self.calculate_directory_metadata(abs_path, skipCache=True, recursiveCalculation=False)

    async def update_directory_metadata_forward(self, directory_path: AbsolutePath) -> None:
        current_path = directory_path
        category = directory_path.category
        if current_path.category in self.settings.get_all_logical_root_paths():
            return
        
        handler = self.resourceHandlerService.get_handler(category)

        while True:
            total_size, last_modified_time = await self.calculate_directory_metadata(
                current_path, skipCache=True, recursiveCalculation=False
            )
            if total_size == -1.0 and last_modified_time == -1.0:
                logger.exception(f"Failed to calculate metadata for {current_path.get_path()}. Stopping forward update.")
                break
            await self.set_metadata(category, current_path.DB_format_path(), total_size, last_modified_time)

            current_db_path = current_path.DB_format_path()
            if current_db_path in self.settings.get_all_logical_root_paths():
                break
            parent = handler.dirname(current_db_path)
            if not parent or parent == current_db_path:
                break
            current_path.update_path(parent)


@lru_cache
def get_dir_metadata_service() -> DirMetadataService:
    return DirMetadataService()
