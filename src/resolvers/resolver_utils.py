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


async def get_node_list_in_directory(abs_path: str | None, refreshFlag: bool = False) -> list[FileBrowseNode]:
    fileBrowse_nodes: list[FileBrowseNode] = []
    resource_paths = get_settings().resource_paths
    try:
        if abs_path is None:
            for name in resource_paths.keys():
                abs_resource_path = get_absolute_resource_path(name)
                await get_directory_node(abs_resource_path, name, fileBrowse_nodes, refreshFlag)
        else:
            with os.scandir(abs_path) as entries:
                for entry in entries:
                    if entry.is_dir():
                        await get_directory_node(entry.path,entry.name,fileBrowse_nodes, refreshFlag)                        
                    elif entry.is_file() and is_video_file(entry.name):
                        try:
                            stat = entry.stat()
                            video_doc = await VideoModel.get_pymongo_collection().find_one_and_update(
                                {"path": to_local_path(entry.path)},
                                {"$setOnInsert": VideoModel(
                                    path=to_local_path(entry.path),
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
                                    node = await Video.from_mongoDB(VideoModel(**video_doc), getTagsCount=False)
                                )
                            )
                        except DuplicateKeyError:
                            raise DatabaseOperationError(operation="insert_video_document", details=f" file {entry.path}: Duplicate key error.")
                        except (OSError, Exception):
                            raise FileBrowseError(f"Error accessing file {entry.path}")
    except (OSError, Exception):
        raise FileBrowseError(f"Error accessing directory {abs_path}")
    
    return fileBrowse_nodes


# util functions

async def get_directory_node(path: str, name:str, fileBrowse_nodes: list[FileBrowseNode], refreshFlag: bool = False):
    # Calculate total size and last modified time of all videos under this directory
    total_size, last_modified_time = await run_in_threadpool(
        get_total_size_and_last_modified_time,
        get_path_standard_format(path),

    )
    
    if total_size > 0:
        fileBrowse_nodes.append(
            FileBrowseNode(
                node = Video.create_new(
                    id=strawberry.ID(str(ObjectId())),
                    name=name,
                    isDir=True,
                    lastModifyTime=last_modified_time,
                    size=total_size
                )
            )
        )

def is_video_file(filename: str) -> bool:
    # Helper function to check if a file is a video based on its extension.
    _, ext = os.path.splitext(filename.lower())
    return ext in get_settings().video_extensions

def get_path_standard_format(path: str) -> str:
        """Standardize path format"""
        return os.path.normpath(path).replace("\\", "/")

async def get_top_tag_docs(limit: int, findQuery = None) -> list[VideoTagModel] :
    if not findQuery:
        findQuery = VideoTagModel.find()
    return await findQuery.sort([("count", -1)]).limit(limit).to_list()

def _get_total_size_and_last_modified_time_impl(directory_path: str) -> tuple[float, float]:
    total_size = 0.0
    last_modified_time = 0.0

    try:
        with os.scandir(directory_path) as entries:
            for entry in entries:
                if entry.is_dir():
                    dir_size, dir_mtime = get_total_size_and_last_modified_time(
                        get_path_standard_format(entry.path)
                    )
                    total_size += dir_size
                    last_modified_time = max(last_modified_time, dir_mtime)
                elif entry.is_file() and is_video_file(entry.name):
                        stat = entry.stat()
                        total_size += stat.st_size
                        last_modified_time = max(last_modified_time, stat.st_mtime)
    
        # If no videos found, use the folder's modification time
        if last_modified_time == 0.0:
                stat = os.stat(directory_path)
                last_modified_time = stat.st_mtime
    except (OSError, Exception):
        # If any error occurs (e.g., permission denied), log and return 0 size and time
        print(f"Error accessing directory {directory_path} to calculate size and last modified time.")
        
    return total_size, last_modified_time


# cache for directory size and last modified time (5 min TTL, max 1024 entries)
_dir_cache: TTLCache[str, tuple[float, float]] = TTLCache(maxsize=1024, ttl=300)

def get_total_size_and_last_modified_time(directory_path: str, refreshFlag: bool = False) -> tuple[float, float]:
    """
    Get total size and last modified time of all video files under the given directory.
    Uses caching to avoid redundant calculations.
    """
    if not refreshFlag and directory_path in _dir_cache:
        return _dir_cache[directory_path]

    result = _get_total_size_and_last_modified_time_impl(directory_path)
    _dir_cache[directory_path] = result
    return result


# def clear_dir_cache():
#     """Clear the directory size and last modified time cache."""
#     _dir_cache.clear()


def get_absolute_resource_path(pseudo_root_dir_name: str) -> str:
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
    
    return get_path_standard_format(abs_path)

def to_mounted_path(local_path: str) -> str:
    """Convert absolute path to mounted path in container if root_path is set"""
    settings = get_settings()
    mounted_path = local_path
    if settings.root_path:
        for pseudo_name, resource_path in settings.resource_paths.items():
            if mounted_path.startswith(resource_path):
                relative_sub_path = mounted_path[len(resource_path):]
                return get_path_standard_format(os.path.join(settings.root_path, pseudo_name, relative_sub_path.lstrip("/")))
    return mounted_path

def to_local_path(mounted_path: str) -> str:
    """Convert mounted path in container to local absolute path if root_path is set"""
    settings = get_settings()
    local_path = mounted_path
    if settings.root_path:
        for pseudo_name, resource_path in settings.resource_paths.items():
            mounted_root_path = get_path_standard_format(os.path.join(settings.root_path, pseudo_name))
            if local_path.startswith(mounted_root_path):
                relative_sub_path = local_path[len(mounted_root_path):]
                return get_path_standard_format(os.path.join(resource_path, relative_sub_path.lstrip("/")))
    return local_path