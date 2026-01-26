from functools import lru_cache
import os

from bson import ObjectId
from cachetools import TTLCache
from fastapi.concurrency import run_in_threadpool
from pymongo.errors import DuplicateKeyError
import strawberry
from src.config import get_settings
from src.db.models.Video_model import VideoModel, VideoTagModel
from src.errors import DatabaseOperationError, FileBrowseError
from src.schema.types.fileBrowse_type import FileBrowseNode
from src.schema.types.video_type import Video
from src.logger import get_logger

logger = get_logger("resolver_utils")


# cache for directory size and last modified time
_dir_cache: TTLCache[str, tuple[float, float]] = TTLCache(
    maxsize=get_settings().cache_config.max_size, 
    ttl=get_settings().cache_config.ttl
)

class ResolverUtils:

    # ============================================================
    # Browse file utils
    # ============================================================

    async def get_node_list_in_directory(self, abs_path: str | None, refreshFlag: bool = False) -> list[FileBrowseNode]:
        fileBrowse_nodes: list[FileBrowseNode] = []
        resource_paths = get_settings().resource_paths
        try:
            if abs_path is None:
                for name in resource_paths.keys():
                    abs_resource_path = self.get_absolute_resource_path(name)
                    await self._get_directory_node(abs_resource_path, name, fileBrowse_nodes, refreshFlag)
            else:
                with os.scandir(abs_path) as entries:
                    while True:
                        try:
                            entry = next(entries)
                            logger.info(f"Processing entry: {entry.path}")
                            if entry.is_dir():
                                await self._get_directory_node(entry.path, entry.name, fileBrowse_nodes, refreshFlag)
                            elif entry.is_file() and self.is_video_file(entry.name):
                                    stat = entry.stat()
                                    video_doc = await VideoModel.get_pymongo_collection().find_one_and_update(
                                        {"path": self.to_host_path(entry.path)},
                                        {"$setOnInsert": VideoModel(
                                            path=self.to_host_path(entry.path),
                                            name=entry.name,
                                            isDir=False,
                                            lastModifyTime=stat.st_mtime,
                                            size=stat.st_size,
                                            tags=[]
                                        ).model_dump()},
                                        upsert=True, return_document=True
                                    )

                                    fileBrowse_nodes.append(
                                        FileBrowseNode(
                                            node=await Video.from_mongoDB(VideoModel(**video_doc), getTagsCount=False)
                                        )
                                    )
                        except StopIteration:
                            break
                        except OSError as e:
                            logger.error(f"Error processing file {entry.path}: {e}")
                            # Skip this entry if any error occurs
                            continue

        except (OSError, Exception) as e:
            logger.error(f"Error accessing directory {abs_path}: {e}")
            raise FileBrowseError(f"Error accessing directory {abs_path}")
        
        logger.info(f"Cached size: {_dir_cache.currsize}/{_dir_cache.maxsize}")
        return fileBrowse_nodes

    async def _get_directory_node(self, path: str, name: str, fileBrowse_nodes: list[FileBrowseNode], refreshFlag: bool = False):
        """Calculate total size and last modified time of all videos under this directory"""
        total_size, last_modified_time = await run_in_threadpool(
            self.get_total_size_and_last_modified_time,
            self.get_path_standard_format(path),
            refreshFlag
        )
        # Append directory node only when there is at least one video file inside or
        if total_size != 0.0 and last_modified_time != 0.0:
            fileBrowse_nodes.append(
                FileBrowseNode(
                    node=Video.create_new(
                        id=strawberry.ID(str(ObjectId())),
                        name=name,
                        isDir=True,
                        lastModifyTime=last_modified_time,
                        size=total_size
                    )
                )
            )

    def is_video_file(self, filename: str) -> bool:
        """Helper function to check if a file is a video based on its extension."""
        _, ext = os.path.splitext(filename.lower())
        return ext in get_settings().video_extensions

    # ============================================================
    # Execute tags query
    # ============================================================

    async def get_top_tag_docs(self, limit: int, findQuery=None) -> list[VideoTagModel]:
        if not findQuery:
            findQuery = VideoTagModel.find()
        return await findQuery.sort([("count", -1)]).limit(limit).to_list()

    # ============================================================
    # Calculate directory size and last modified time with caching
    # ============================================================

    def get_total_size_and_last_modified_time(self, directory_path: str, refreshFlag: bool = False) -> tuple[float, float]:
        """
        Get total size and last modified time of all video files under the given directory.
        Uses caching to avoid redundant calculations.
        """
        if not refreshFlag and directory_path in _dir_cache:
            return _dir_cache.get(directory_path)

        result = self._get_total_size_and_last_modified_time_impl(directory_path, refreshFlag)
        _dir_cache.update({directory_path: result})
        
        return result

    def _get_total_size_and_last_modified_time_impl(self, directory_path: str, refreshFlag: bool) -> tuple[float, float]:
        total_size = 0.0
        last_modified_time = 0.0
        
        def calculate_entry():
            nonlocal total_size, last_modified_time
            try:
                with os.scandir(directory_path) as entries:
                    for entry in entries:
                        if entry and not refreshFlag:
                            total_size = -1.0
                            last_modified_time = -1.0
                            return
                        
                        if entry.is_dir():
                            dir_size, dir_mtime = self.get_total_size_and_last_modified_time(
                                self.get_path_standard_format(entry.path),
                                refreshFlag
                            )
                            total_size += dir_size
                            last_modified_time = max(last_modified_time, dir_mtime)
                        elif entry.is_file() and self.is_video_file(entry.name):
                            stat = entry.stat()
                            total_size += stat.st_size
                            last_modified_time = max(last_modified_time, stat.st_mtime)

            except (OSError, Exception):
                # If any error occurs (e.g., permission denied), log and return 0 size and time
                logger.error(f"Error accessing directory {directory_path} to calculate size and last modified time.")
                total_size = -1.0
                last_modified_time = -1.0

        calculate_entry()
        
        return total_size, last_modified_time

    # ============================================================
    # Path conversion utils
    # ============================================================

    def get_path_standard_format(self, path: str) -> str:
        """Standardize path format"""
        return os.path.normpath(path).replace("\\", "/")
    
    def get_absolute_resource_path(self, pseudo_root_dir_name: str) -> str:
        """Get the absolute resource path from pseudo root dir name and sub path"""
        settings = get_settings()
        resource_paths = settings.resource_paths

        if pseudo_root_dir_name not in resource_paths:
            raise FileBrowseError(f"Pseudo root dir name '{pseudo_root_dir_name}' not found in resource paths.")

        if settings.root_path:
            # Use root_path as base path when provided (run in container)
            abs_path = os.path.join(settings.root_path, pseudo_root_dir_name)
        else:
            # Use configured resource path directly (run locally)
            abs_path = resource_paths[pseudo_root_dir_name]

        return self.get_path_standard_format(abs_path)

    def to_mounted_path(self, local_path: str) -> str:
        """Convert absolute path to mounted path in container if root_path is set"""
        settings = get_settings()
        mounted_path = local_path
        if settings.root_path:
            for pseudo_name, resource_path in settings.resource_paths.items():
                if mounted_path.startswith(resource_path):
                    relative_sub_path = mounted_path[len(resource_path):]
                    return self.get_path_standard_format(os.path.join(settings.root_path, pseudo_name, relative_sub_path.lstrip("/")))
        return self.get_path_standard_format(mounted_path)

    def to_host_path(self, mounted_path: str) -> str:
        """Convert mounted path in container to local absolute path if root_path is set"""
        settings = get_settings()
        local_path = mounted_path
        if settings.root_path:
            for pseudo_name, resource_path in settings.resource_paths.items():
                mounted_root_path = self.get_path_standard_format(os.path.join(settings.root_path, pseudo_name))
                if local_path.startswith(mounted_root_path):
                    relative_sub_path = local_path[len(mounted_root_path):]
                    return self.get_path_standard_format(os.path.join(resource_path, relative_sub_path.lstrip("/")))
        return self.get_path_standard_format(local_path)

    # ============================================================
    # Video MIME type utils
    # ============================================================

    def get_video_mime_type(self, file_path: str) -> str:
        """
        Returns the correct MIME type based on the file extension.

        Args:
            file_path: Video file path

        Returns:
            str: MIME type string
        """
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".ogg": "video/ogg",
            ".ogv": "video/ogg",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".wmv": "video/x-ms-wmv",
            ".flv": "video/x-flv",
            ".mkv": "video/x-matroska",
            ".m4v": "video/x-m4v",
            ".mpg": "video/mpeg",
            ".mpeg": "video/mpeg",
        }
        return mime_types.get(ext, "video/mp4")

@lru_cache
def resolver_utils() -> ResolverUtils:
    return ResolverUtils()
