from functools import lru_cache
import os
from pymongo import UpdateOne
from src.services.cache_service import get_cache_service, CacheService
from src.config import get_settings
from src.db.models.DirMetadata_model import DirMetadataModel
from src.logger import get_logger
from src.services.path_convert_service import get_path_service

logger = get_logger("dir_metadata_service")


class DirMetadataService:

    def __init__(self):
        self._cache: CacheService = get_cache_service()
        self.pathHelper = get_path_service()

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
            logger.exception(f"Bulk write error during dir metadata upsert: {e}")

        for path, value in entries.items():
            self._cache.set(path, value)

    async def calculate_directory_metadata(self, 
                                           directory_path: str, 
                                           skipCache: bool = False,
                                           recursiveCalculation: bool = True) -> tuple[float, float]:
        """
        Get total size and last modified time of all video files under the given directory.
        Uses Cache-Aside pattern: cache -> database -> filesystem scan.

        :param directory_path: Absolute path of the directory to calculate metadata for
        :param skipCache: If True, bypass cache and get fresh data from filesystem
        :param recursiveCalculation: If True, calculate metadata recursively for all subdirectories; if False, only calculate for the specified directory without going into subdirectories
        :return: Tuple of (total size in bytes, last modified time as timestamp)
        :rtype: tuple[float, float]
        """
        service = get_dir_metadata_service()
        if not skipCache:
            cached = await service.get_metadata(directory_path)
            if cached is not None:
                return cached

        collected: dict[str, tuple[float, float]] = {}
        result = await self._calculate_directory_metadata_impl(directory_path, collected, recursiveCalculation)
        collected[directory_path] = result
        await service.bulk_set_metadata(collected)
        return result

    async def _calculate_directory_metadata_impl(self, 
                                           directory_path: str, 
                                           collected: dict[str, tuple[float, float]],
                                           recursiveCalculation: bool) -> tuple[float, float]:
        total_size = 0.0
        last_modified_time = 0.0

        try:
            with os.scandir(directory_path) as entries:
                for entry in entries:
                    if entry.is_dir():
                        sub_path = self.pathHelper.get_path_standard_format(entry.path)
                        if recursiveCalculation:
                            dir_size, dir_mtime = await self._calculate_directory_metadata_impl(
                                sub_path, collected, recursiveCalculation
                            )
                        else:
                            dir_size, dir_mtime = await get_dir_metadata_service().get_metadata(sub_path) or (0.0, 0.0)
                        collected[sub_path] = (dir_size, dir_mtime)
                        total_size += dir_size
                        last_modified_time = max(last_modified_time, dir_mtime)
                    elif entry.is_file() and self.pathHelper.is_video_file(entry.name):
                        stat = entry.stat()
                        total_size += stat.st_size
                        last_modified_time = max(last_modified_time, stat.st_mtime)

        except (OSError, Exception):
            # On error, log and return -1 to indicate failure
            logger.exception(f"Error accessing directory {directory_path} to calculate size and last modified time.")
            total_size = -1.0
            last_modified_time = -1.0

        return total_size, last_modified_time

    async def update_directory_metadata_forward(self, directory_path: str) -> None:
        service = get_dir_metadata_service()
        current_path = directory_path

        while True:
            total_size, last_modified_time = await self.calculate_directory_metadata(
                current_path, skipCache=True, recursiveCalculation=False
            )
            # If calculation failed, stop propagation
            if total_size == -1.0 and last_modified_time == -1.0:
                logger.exception(f"Failed to calculate metadata for {current_path}. Stopping forward update.")
                break
            # Here we don't use bulkwrite to update both cache and database to ensure consistency 
            # so that for each iteration the method calculation_directory_metadata can get the newly updated metadata
            await service.set_metadata(current_path, total_size, last_modified_time)
            
            # Get corresponding root resource path for parent directory
            root_resource_paths = get_settings().resource_paths.values()
            if current_path in root_resource_paths:
                break
            current_path = os.path.dirname(current_path)


@lru_cache
def get_dir_metadata_service() -> DirMetadataService:
    return DirMetadataService()
