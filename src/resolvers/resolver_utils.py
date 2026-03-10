import asyncio
from functools import lru_cache
import os

from bson import ObjectId
from fastapi.concurrency import run_in_threadpool
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
import strawberry
from src.config import get_settings
from src.db.models.Video_model import VideoModel
from src.db.models.VideoTag_model import VideoTagModel
from src.errors import FileBrowseError
from src.resolvers.thumbnail_resolver import get_thumbnail_resolver
from src.schema.types.fileBrowse_type import FileBrowseNode
from src.schema.types.pydantic_types.batch_operation_type import TagsOperationMappingInputModel
from src.schema.types.pydantic_types.fileBrowe_type import RelativePathInputModel
from src.schema.types.video_type import Video
from src.cache.dir_metadata_service import get_dir_metadata_service
from src.logger import get_logger

logger = get_logger("resolver_utils")

class ResolverUtils:

    # ============================================================
    # Browse file utils
    # ============================================================

    async def get_node_list_in_directory(self, 
                                         abs_path: str | None, 
                                         skipCache: bool = False,
                                         recursiveCalculation: bool = True
                                         ) -> list[FileBrowseNode]:
        fileBrowse_nodes: list[FileBrowseNode] = []
        resource_paths = get_settings().resource_paths
        try:
            if abs_path is None:
                for name in resource_paths.keys():
                    abs_root_resource_path = self.get_absolute_root_resource_path(name)
                    await self._get_directory_node(
                        abs_root_resource_path, 
                        name, 
                        fileBrowse_nodes, 
                        skipCache, 
                        recursiveCalculation
                    )
            else:
                with os.scandir(abs_path) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir():
                                await self._get_directory_node(
                                    entry.path, 
                                    entry.name, 
                                    fileBrowse_nodes, 
                                    skipCache,
                                    recursiveCalculation
                                )
                            elif entry.is_file() and self.is_video_file(entry.name):
                                stat = entry.stat()
                                video_doc = await VideoModel.get_pymongo_collection().find_one_and_update(
                                    {"path": self.to_host_path(entry.path)},
                                    {"$setOnInsert": VideoModel(
                                        path=self.to_host_path(entry.path),
                                        name=os.path.basename(entry.path),
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
                        except OSError as e:
                            logger.error(f"Error processing file {entry.path}: {e}")
                            continue
                
                # After processing all entries, update the directory metadata for "abs_path"
                # to ensure cachea and database are updated if there are new files
                await resolver_utils().calculate_directory_metadata(
                    abs_path, 
                    skipCache=skipCache, 
                    recursiveCalculation=recursiveCalculation
                )

        except (OSError, Exception) as e:
            logger.error(f"Error accessing directory {abs_path}: {e}")
            raise FileBrowseError(f"Error accessing directory {abs_path}")
        
        return fileBrowse_nodes

    async def _get_directory_node(self, 
                                  path: str, 
                                  name: str, 
                                  fileBrowse_nodes: list[FileBrowseNode], 
                                  skipCache: bool,
                                  recursiveCalculation: bool):
        """Calculate total size and last modified time of all videos under this directory"""
        total_size, last_modified_time = await self.calculate_directory_metadata(
            self.get_path_standard_format(path),
            skipCache=skipCache,
            recursiveCalculation=recursiveCalculation
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
    
    def get_all_video_entries_in_directory(self, directory_path: str) -> list[os.DirEntry[str]]:
        """Get all video file entries under the given directory and its subdirectories."""
        video_entries: list[os.DirEntry[str]] = []
        try:
            with os.scandir(directory_path) as entries:
                for entry in entries:
                    if entry.is_file() and self.is_video_file(entry.name):
                        video_entries.append(entry)
                    elif entry.is_dir():
                        video_entries.extend(
                            self.get_all_video_entries_in_directory(
                                self.get_path_standard_format(entry.path)
                            )
                        )
        except (OSError, Exception):
            logger.error(f"Error accessing directory {directory_path} to get video entries.")
        
        return video_entries

    def is_video_file(self, filename: str) -> bool:
        """Helper function to check if a file is a video based on its extension."""
        _, ext = os.path.splitext(filename.lower())
        return ext in get_settings().video_extensions

    # ============================================================
    # Create and/or execute queries
    # ============================================================

    async def get_top_tag_docs(self, limit: int, findQuery=None) -> list[VideoTagModel]:
        if not findQuery:
            findQuery = VideoTagModel.find()
        return await findQuery.sort([("count", -1)]).limit(limit).to_list()
    
    async def update_tag_counts(self, update_tags: dict[str, tuple[int,bool]]) -> None:
        """
        update the tag counts in the database based on the changes in tags using bulk write.

        :param update_tags: Dictionary mapping tag names to a tuple of (count change, is_increment).
        :type update_tags: dict[str, tuple[int,bool]]
        :return: None
        :rtype: None
        """
        operations = []

        for tag_name, (count_change, is_increment) in update_tags.items():
            if is_increment:
                operations.append(
                    UpdateOne(
                        {"name": tag_name},
                        {"$inc": {"count": count_change}},
                        upsert=True
                    )
                )
            else:
                operations.append(
                    UpdateOne(
                        {"name": tag_name},
                        {"$inc": {"count": -count_change}}
                    )
                )

        try:
            if operations:
                await VideoTagModel.get_pymongo_collection().bulk_write(operations)

            # delete tags with non-positive counts
            decremented_tags = [tag for tag, (_, is_inc) in update_tags.items() if not is_inc]
            if decremented_tags:
                await VideoTagModel.find({"count": {"$lte": 0}}).delete()
        
        except BulkWriteError as bwe:
            logger.error(f"Bulk write error during tag counts update: {bwe.details}")
        except Exception as e:
            logger.error(f"Error during bulk update of tag counts: {e}")

    def _track_tag_change(self, update_tags: dict[str, tuple[int, bool]], tags: set[str], is_increment: bool):
        for tag in tags:
            tag_record: tuple[int, bool] | None = update_tags.get(tag)
            update_tags[tag] = (tag_record[0] + 1, is_increment) if tag_record else (1, is_increment)

    async def process_new_video_entry(
        self,
        entry: os.DirEntry[str],
        author: str | None,
        tagsOperation: TagsOperationMappingInputModel | None,
        update_tags: dict[str, tuple[int,bool]]
    ) -> UpdateOne:
        """
        Process a single new video entry: get duration via ffprobe and build upsert operation.

        :param entry: Directory entry for the video file
        :param author: Author name to set (if provided)
        :param tagsOperation: Tags operation to apply
        :param track_tag_change: Callback to track tag changes
        :return: UpdateOne operation for bulk write
        """
        host_path = self.to_host_path(entry.path)
        filter_query = {"path": host_path}

        # Get video duration with semaphore to limit concurrent ffprobe processes
        duration = await get_thumbnail_resolver().get_video_duration(entry.path) or 0.0

        stat = entry.stat()
        set_on_insert = VideoModel(
            name=entry.name,
            path=host_path,
            isDir=False,
            lastModifyTime=stat.st_mtime,
            size=stat.st_size,
            duration=duration,
            tags=[]
        ).model_dump()

        if author is not None:
            set_on_insert["author"] = author

        if tagsOperation is not None:
            tags_set = set(tagsOperation.tags)
            if tagsOperation.append:
                set_on_insert["tags"] = list(tags_set)
                self._track_tag_change(update_tags, tags_set, True)

        return UpdateOne(filter_query, {"$setOnInsert": set_on_insert}, upsert=True)
    
    def remove_videos_by_paths(self, paths: list[str]):
        try:
            for path in paths:
                os.remove(self.to_mounted_path(path))
        except Exception as e:
            logger.error(f"Error removing video files: {e}")
            raise FileBrowseError("Error removing video files.")

    # ============================================================
    # Calculate directory size and last modified time with caching
    # ============================================================

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
        result = await run_in_threadpool(
            self._calculate_directory_metadata_impl, directory_path, collected, recursiveCalculation
        )
        collected[directory_path] = result
        await service.bulk_set_metadata(collected)
        return result

    def _calculate_directory_metadata_impl(self, 
                                           directory_path: str, 
                                           collected: dict[str, tuple[float, float]],
                                           recursiveCalculation: bool) -> tuple[float, float]:
        total_size = 0.0
        last_modified_time = 0.0

        try:
            with os.scandir(directory_path) as entries:
                for entry in entries:
                    if entry.is_dir():
                        sub_path = self.get_path_standard_format(entry.path)
                        if recursiveCalculation:
                            dir_size, dir_mtime = self._calculate_directory_metadata_impl(
                                sub_path, collected, recursiveCalculation
                            )
                        else:
                            loop = asyncio.get_event_loop()
                            dir_size, dir_mtime = loop.run_until_complete(
                                get_dir_metadata_service().get_metadata(sub_path)
                            ) or (0.0, 0.0)
                        collected[sub_path] = (dir_size, dir_mtime)
                        total_size += dir_size
                        last_modified_time = max(last_modified_time, dir_mtime)
                    elif entry.is_file() and self.is_video_file(entry.name):
                        stat = entry.stat()
                        total_size += stat.st_size
                        last_modified_time = max(last_modified_time, stat.st_mtime)

        except (OSError, Exception):
            # On error, log and return -1 to indicate failure
            logger.error(f"Error accessing directory {directory_path} to calculate size and last modified time.")
            total_size = -1.0
            last_modified_time = -1.0

        return total_size, last_modified_time

    # ============================================================
    # Path conversion utils
    # ============================================================

    def get_path_standard_format(self, path: str) -> str:
        """Standardize path format"""
        return os.path.normpath(path).replace("\\", "/")
    
    def get_absolute_root_resource_path(self, pseudo_root_dir_name: str) -> str:
        """Get the absolute resource path from pseudo root dir name and sub path"""
        settings = get_settings()
        resource_paths = settings.resource_paths

        if pseudo_root_dir_name not in resource_paths:
            raise FileBrowseError(f"Pseudo root dir name '{pseudo_root_dir_name}' not found in resource paths.")

        if settings.ROOT_PATH:
            # Use ROOT_PATH as base path when provided (run in container)
            abs_path = os.path.join(settings.ROOT_PATH, pseudo_root_dir_name)
        else:
            # Use configured resource path directly (run locally)
            abs_path = resource_paths[pseudo_root_dir_name]

        return self.get_path_standard_format(abs_path)
    
    def get_absolute_resource_path(self, relativePathInputModel: RelativePathInputModel) -> str:
        if relativePathInputModel.parsedPath is None:
            abs_path = None  # Browse root directories
        else:
            pseudo_root_dir_name, sub_path = relativePathInputModel.parsedPath
            abs_resource_path = resolver_utils().get_absolute_root_resource_path(pseudo_root_dir_name)
            
            if sub_path is None:
                abs_path = abs_resource_path
            else:
                abs_path = abs_resource_path + sub_path

        return abs_path

    def to_mounted_path(self, local_path: str) -> str:
        """Convert absolute path to mounted path in container if ROOT_PATH is set"""
        settings = get_settings()
        mounted_path = local_path
        if settings.ROOT_PATH:
            for pseudo_name, resource_path in settings.resource_paths.items():
                if mounted_path.startswith(resource_path):
                    relative_sub_path = mounted_path[len(resource_path):]
                    return self.get_path_standard_format(os.path.join(settings.ROOT_PATH, pseudo_name, relative_sub_path.lstrip("/")))
        return self.get_path_standard_format(mounted_path)

    def to_host_path(self, mounted_path: str) -> str:
        """Convert mounted path in container to local absolute path if ROOT_PATH is set"""
        settings = get_settings()
        local_path = mounted_path
        if settings.ROOT_PATH:
            for pseudo_name, resource_path in settings.resource_paths.items():
                mounted_ROOT_PATH = self.get_path_standard_format(os.path.join(settings.ROOT_PATH, pseudo_name))
                if local_path.startswith(mounted_ROOT_PATH):
                    relative_sub_path = local_path[len(mounted_ROOT_PATH):]
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
