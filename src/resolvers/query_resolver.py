import os
from fastapi.concurrency import run_in_threadpool
from pymongo.errors import DuplicateKeyError
import strawberry
from bson import ObjectId
from src.config import get_settings
from src.schema.types.fileBrowse_type import FileBrowseNode, RelativePathInput
from src.schema.types.search_type import (
    SearchFrom,
    SuggestionInput,
    VideoSearchInput,
    VideoSearchResult,
    VideoSortOption,
    SearchField,
    Pagination
)
from src.schema.types.video_type import Video, VideoTag
from src.db.models.Video_model import VideoModel, VideoTagModel
from src.errors import DatabaseOperationError, FileBrowseError, InvalidPathError, VideoNotFoundError

class QueryResolver:

    async def resolve_search_videos(self,input: VideoSearchInput) -> VideoSearchResult:
        """
        Resolve function to search for videos based on various criteria.

        :param input: Filter criteria for searching videos.
        :type input: VideoSearchInput
        :return: Search results for videos.
        :rtype: VideoSearchResult
        """
        settings = get_settings()
        query_filters = {}

        # build query
        if input.titleKeyword.keyWord:
            query_filters["name"] = {"$regex": input.titleKeyword.keyWord, "$options": "i"}
        if input.author.keyWord:
            query_filters["author"] = {"$regex": input.author.keyWord, "$options": "i"}
        if input.tags:
            query_filters["tags"] = {"$all": input.tags}
        if input.sortBy == VideoSortOption.LOVED:
            query_filters["loved"] = True

        sort_mapping = {
            VideoSortOption.LATEST: [("lastViewTime", -1)],
            VideoSortOption.MOST_VIEWED: [("viewCount", -1), ("lastViewTime", -1)],
            VideoSortOption.LOVED: [("loved", -1), ("lastViewTime", -1)]
        }
        sort_criteria = sort_mapping.get(input.sortBy, [("lastModifyTime", -1)])

        if input.fromPage == SearchFrom.FrontalPage:
            page_size = settings.page_size_default.homepage_videos
        else:
            page_size = settings.page_size_default.searchpage
        page_number = input.currentPageNumber or 1
        skip = (page_number - 1) * page_size

        try:
            # execute query
            query = VideoModel.find(query_filters)
            total_count = await query.count()
            for field, order in sort_criteria:
                query = query.sort((field, order))
            video_models = await query.skip(skip).limit(page_size).to_list()

            # build results
            videos = [await Video.from_mongoDB(vm) for vm in video_models]
            pagination = Pagination(
                size=page_size,
                totalCount=total_count,
                currentPageNumber=page_number
            )

            return VideoSearchResult(pagination=pagination, videos=videos)
        except Exception:
            raise DatabaseOperationError(operation="video search", 
                                         details=f"Filters-{query_filters}, Sort-{sort_criteria}, Skip-{skip}, Limit-{page_size}")

    async def resolve_get_top_tags(self) -> list[VideoTag]:
        """
        Resolve function to retrieve the top video tags.

        :return: List of top video tags.
        :rtype: list[VideoTag]
        """
        settings = get_settings()
        limit = settings.page_size_default.homepage_tags
        try:
            tag_docs = await get_top_tag_docs(limit)
            return [VideoTag(name=tag.name, count=tag.tag_count) for tag in tag_docs]
        except Exception:
            raise DatabaseOperationError(operation="get top tags",
                                         details=f"Limit-{limit}")

    async def resolve_get_suggestions(self,input: SuggestionInput) -> list[str]:
        """
        Resolve function to get suggestions based on a keyword and suggestion type.

        :param input: Input containing the keyword and suggestion type.
        :type input: SuggestionInput
        :return: Suggestion results.
        :rtype: SuggestionResults
        """
        settings = get_settings()
        if input.keyword.keyWord:
            keyword = input.keyword.keyWord
        else:
            return []
        suggestion_type = input.suggestionType

        limits = settings.suggestion_limit

        try:
            match suggestion_type:

                case SearchField.TAG:
                    limit = limits.tag
                    if not keyword:
                        tag_docs = await get_top_tag_docs(limit)
                        return [tag.name for tag in tag_docs]

                    prefix_query = VideoTagModel.find(
                        {"name" : {"$regex": f"^{keyword}", "$options":"i"}}
                    )
                    prefix_matches = await get_top_tag_docs(limit,prefix_query)
                    prefix_matches_names = [tag.name for tag in prefix_matches]

                    if limit - len(prefix_matches_names) > 0:
                        contains_query = VideoTagModel.find(
                            {"name": {"$regex": f".*{keyword}.*", "$options":"i", "$nin": prefix_matches_names}}
                        )
                        contains_matches = await get_top_tag_docs(limit, contains_query)
                        prefix_matches_names.extend([tag.name for tag in contains_matches])

                    return prefix_matches_names

                case _:
                    limit = limits.name if suggestion_type == SearchField.NAME else limits.author
                    pipeline = [
                        {"$match": {suggestion_type.value: {"$regex": keyword, "$options": "i"}}},
                        {"$group": {"_id": "$" + suggestion_type.value}},
                        {"$limit": limit}
                    ]
                    collection = VideoModel.get_pymongo_collection()
                    cursor = await collection.aggregate(pipeline)
                    result = []
                    async for doc in cursor:
                        if doc.get("_id"):
                            result.append(doc["_id"])
                    return result
        except Exception:
            raise DatabaseOperationError(operation="get suggestions",
                                         details=f"Keyword-{keyword}, SuggestionType-{suggestion_type}")

        return []

    async def resolve_get_video_by_id(self,videoId: strawberry.ID) -> Video:
        """
        Resolve function to retrieve a video by its ID.

        :param videoId: The ID of the video to retrieve.
        :type videoId: strawberry.ID
        :return: The video corresponding to the given ID.
        :rtype: Video
        """
        try:
            video_model = await VideoModel.get(ObjectId(str(videoId)))
        except Exception:
            raise DatabaseOperationError(operation="get video by id", details=f"videoId-{videoId}")
        
        if not video_model:
            raise VideoNotFoundError(str(videoId))
        return await Video.from_mongoDB(video_model)


    async def resolve_browse_directory(self,path: RelativePathInput) -> list[FileBrowseNode]:
        """
        Resolve function to browse videos in a directory specified by a relative path.

        :param path: The relative path to browse.
        :type path: RelativePathInput
        :return: List of file browse nodes in the specified directory.
        :rtype: list[FileBrowseNode]
        """
        settings = get_settings()
        # Resolve the absolute path from the relative path
        relativePathInoutModel = path.to_pydantic()
        if relativePathInoutModel.parsedPath is None:
            abs_path = None  # Browse root directories
        else:
            pseudo_root_dir_name, sub_path = relativePathInoutModel.parsedPath
            resource_paths_mapping = settings.resource_paths
            if pseudo_root_dir_name not in resource_paths_mapping:
                raise InvalidPathError(f"Invalid pseudo root directory name: {pseudo_root_dir_name}")
            abs_root_path = resource_paths_mapping[pseudo_root_dir_name]
            if sub_path is None:
                abs_path = abs_root_path
            else:
                abs_path = abs_root_path + sub_path

        return await get_node_list_in_directory(abs_path, settings.video_extensions, resource_paths_mapping)


async def get_node_list_in_directory(abs_path: str | None, video_extensions: list[str], resource_paths: dict[str,str]) -> list[FileBrowseNode]:
    fileBrowse_nodes: list[FileBrowseNode] = []
    try:
        if abs_path is None:
            for name,path in resource_paths.items():
                get_directory_node(path,name,video_extensions,fileBrowse_nodes)
        else:
            with os.scandir(abs_path) as entries:
                for entry in entries:
                    if entry.is_dir():
                        get_directory_node(entry.path,entry.name,video_extensions,fileBrowse_nodes)                        
                    elif entry.is_file() and is_video_file(entry.name, video_extensions):
                        try:
                            stat = entry.stat()
                            video_doc = await VideoModel.get_pymongo_collection().find_one_and_update(
                                {"path": get_path_standard_format(entry.path)},
                                {"$setOnInsert": VideoModel(
                                    path=get_path_standard_format(entry.path),
                                    name=entry.name,
                                    isDir=False,
                                    lastModifyTime=stat.st_mtime,
                                    size=stat.st_size
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
                        except OSError:
                            raise FileBrowseError(f"Error accessing file {entry.path}")
    except OSError:
        raise FileBrowseError(f"Error accessing directory {abs_path}")


# util functions

async def get_directory_node(path: str, name:str, video_extensions: list[str], fileBrowse_nodes: list[FileBrowseNode]):
    # Calculate total size and last modified time of all videos under this directory
    total_size, last_modified_time = await run_in_threadpool(
        get_total_size_and_last_modified_time,
        get_path_standard_format(path),
        video_extensions
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

def is_video_file(filename: str, video_extensions: list[str]) -> bool:
    # Helper function to check if a file is a video based on its extension.
    _, ext = os.path.splitext(filename.lower())
    return ext in video_extensions

def get_path_standard_format(path: str) -> str:
        """Standardize path format"""
        return os.path.normpath(path).replace("\\", "/")

async def get_top_tag_docs(limit: int, findQuery = None) -> list[VideoTagModel] :
    if not findQuery:
        findQuery = VideoTagModel.find()
    return await findQuery.sort([("count", -1)]).limit(limit).to_list()

#@cached(TTLCache(maxsize=128, ttl=300))
def get_total_size_and_last_modified_time(directory_path: str, video_extensions: list[str]) -> tuple[float, float]:
    total_size = 0.0
    last_modified_time = 0.0

    try:
        with os.scandir(directory_path) as entries:
            for entry in entries:
                if entry.is_dir():
                    dir_size, dir_mtime = get_total_size_and_last_modified_time(
                        get_path_standard_format(entry.path),
                        video_extensions
                    )
                    total_size += dir_size
                    last_modified_time = max(last_modified_time, dir_mtime)
                elif entry.is_file() and is_video_file(entry.name, video_extensions):
                    try:
                        stat = entry.stat()
                        total_size += stat.st_size
                        last_modified_time = max(last_modified_time, stat.st_mtime)
                    except OSError:
                        raise FileBrowseError(f"Error accessing file-{entry.path}'s metadata")
    except OSError:
        raise FileBrowseError(f"Error accessing directory {directory_path}")
    
    # If no videos found, use the folder's modification time
    if last_modified_time == 0.0:
        try:
            stat = os.stat(directory_path)
            last_modified_time = stat.st_mtime
        except OSError:
            raise FileBrowseError(f"Error getting directory-{directory_path}'s modification time")
        
    return total_size, last_modified_time
    
    # TODO: This function is cached to improve performance when the same directory is accessed multiple times.

    # Explanation: 
    # In the frontend, user can refresh the directory to get updated info of a directory if he wants.
    # Because the total size and last modified time are just indexes to help users know more about the directory
    # Sometimes they not need the most up-to-date info, sometimes they wants to sort all directories and files quickly,
    # it's not necessary to keep them always up-to-date.

    # Idea: use a third-part lib to actively manage the timing of cache invalidation.