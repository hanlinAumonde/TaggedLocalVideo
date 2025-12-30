from fastapi.concurrency import run_in_threadpool
import strawberry
from bson import ObjectId

from src.context import AppContext
from src.resolvers.util import current_directory_context, get_path_standard_format, get_total_size_and_last_modified_time, is_video_file
from src.schema.types.fileBrowse_type import FileBrowseNode, RelativePathInput
from src.schema.types.search_type import (
    SearchFrom,
    SuggestionInput,
    SuggestionResults,
    VideoSearchInput,
    VideoSearchResult,
    VideoSortOption,
    SearchField,
    Pagination
)
from src.schema.types.video_type import Video, VideoTag
from src.db.models.Video_model import VideoModel, VideoTagModel
from src.errors import FileBrowseError, InvalidPathError, VideoNotFoundError


async def resolve_search_videos(input: VideoSearchInput, info: strawberry.Info[AppContext,None]) -> VideoSearchResult:
    """
    Resolve function to search for videos based on various criteria.

    :param input: Filter criteria for searching videos.
    :type input: VideoSearchInput
    :param context: GraphQL context information.
    :type context: strawberry.Info
    :return: Search results for videos.
    :rtype: VideoSearchResult
    """
    query_filters = {}

    # build query
    if input.titleKeyword.keyWord:
        query_filters["name"] = {"$regex": input.titleKeyword.keyWord, "$options": "i"}
    if input.author.keyWord:
        query_filters["author"] = {"$regex": input.author.keyWord, "$options": "i"}
    if input.tags:
        query_filters["tags"] = {"$all": input.tags}

    sort_mapping = {
        VideoSortOption.LATEST: [("lastModifyTime", -1)],
        VideoSortOption.MOST_VIEWED: [("viewCount", -1), ("lastModifyTime", -1)],
        VideoSortOption.LOVED: [("loved", -1), ("lastViewTime", -1)]
    }
    sort_criteria = sort_mapping.get(input.sortBy, [("lastModifyTime", -1)])

    if input.fromPage == SearchFrom.FrontalPage:
        page_size = info.context.pagination_sizes.get("homepage_videos", 5)
    else:
        page_size = info.context.pagination_sizes.get("searchpage", 15)
    page_number = input.currentPageNumber or 1
    skip = (page_number - 1) * page_size

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

async def resolve_get_top_tags(info: strawberry.Info[AppContext,None]) -> list[VideoTag]:
    """
    Resolve function to retrieve the top video tags.

    :param context: GraphQL context information.
    :type context: strawberry.Info
    :return: List of top video tags.
    :rtype: list[VideoTag]
    """
    limit = info.context.pagination_sizes.get("homepage_tags", 20)
    tag_models = await VideoTagModel.find().sort([("tag_count", -1)]).limit(limit).to_list()
    return [VideoTag(name=tag.name, count=tag.tag_count) for tag in tag_models]

async def resolve_get_suggestions(input: SuggestionInput, info: strawberry.Info[AppContext,None]) -> SuggestionResults:
    """
    Resolve function to get suggestions based on a keyword and suggestion type.

    :param input: Input containing the keyword and suggestion type.
    :type input: SuggestionInput
    :param context: GraphQL context information.
    :type context: strawberry.Info
    :return: Suggestion results.
    :rtype: SuggestionResults
    """
    if input.keyword.keyWord:
        keyword = input.keyword.keyWord
    else:
        return SuggestionResults(results=[])
    suggestion_type = input.suggestionType

    limits = info.context.suggestion_limits

    match suggestion_type:

        case SearchField.TITLE:
            limit = limits.get("name", 10)
            pipeline = [
                {"$match": {"name": {"$regex": keyword, "$options": "i"}}},
                {"$group": {"_id": "$name"}},
                {"$limit": limit}
            ]
            result = await VideoModel.aggregate(pipeline).to_list()
            results = [doc["_id"] for doc in result if doc["_id"]]
            return SuggestionResults(results=results)
        
        case SearchField.AUTHOR:
            limit = limits.get("author", 10)
            pipeline = [
                {"$match": {"author": {"$regex": keyword, "$options": "i"}}},
                {"$group": {"_id": "$author"}},
                {"$limit": limit}
            ]
            result = await VideoModel.aggregate(pipeline).to_list()
            results = [doc["_id"] for doc in result if doc["_id"]]
            return SuggestionResults(results=results)
        
        case SearchField.TAGS:
            limit = limits.get("tag", 20)
            tags = await VideoTagModel.find(
                {"name": {"$regex": keyword, "$options": "i"}}
            ).sort([("tag_count", -1)]).limit(limit).to_list()
            results = [VideoTag(name=tag.name, count=tag.tag_count) for tag in tags]
            return SuggestionResults(results=results)

    return SuggestionResults(results=[])

async def resolve_get_video_by_id(videoId: strawberry.ID) -> Video:
    """
    Resolve function to retrieve a video by its ID.

    :param videoId: The ID of the video to retrieve.
    :type videoId: strawberry.ID
    :return: The video corresponding to the given ID.
    :rtype: Video
    """
    video_model = await VideoModel.get(ObjectId(str(videoId)))
    if not video_model:
        raise VideoNotFoundError(str(videoId))
    return await Video.from_mongoDB(video_model)


async def resolve_browse_directory(path: RelativePathInput, info: strawberry.Info[AppContext, None]) -> list[FileBrowseNode]:
    """
    Resolve function to browse videos in a directory specified by a relative path.
    
    :param path: The relative path to browse.
    :type path: RelativePathInput
    :param context: GraphQL context information.
    :type context: strawberry.Info
    :return: List of file browse nodes in the specified directory.
    :rtype: list[FileBrowseNode]
    """
    # Resolve the absolute path from the relative path
    relativePathInoutModel = path.to_pydantic()
    if relativePathInoutModel.parsed_path is None:
        abs_path = None  # Browse root directories
    else:
        pseudo_root_dir_name, sub_path = relativePathInoutModel.parsed_path
        resource_paths_mapping = info.context.resource_paths
        if pseudo_root_dir_name not in resource_paths_mapping:
            raise InvalidPathError(f"Invalid pseudo root directory name: {pseudo_root_dir_name}")
        abs_root_path = resource_paths_mapping[pseudo_root_dir_name]
        if sub_path is None:
            abs_path = abs_root_path
        else:
            abs_path = abs_root_path + sub_path
    
    return await get_node_list_in_directory(abs_path, info.context.video_extensions, resource_paths_mapping)


async def get_node_list_in_directory(abs_path: str | None, video_extensions: list[str], resource_paths: dict) -> list[FileBrowseNode]:
    # Helper function to get the list of FileBrowseNode in a directory given its absolute path.
    # 1. Query the file system to get the list of files(only videos) and directories in the specified path
    # Attention: If the path is empty, it means browsing the root directories provided by the configuration
    fileBrowse_nodes: list[FileBrowseNode] = []
    try:
        with current_directory_context(abs_path, resource_paths) as entries:
            for entry in entries:
                if entry.is_dir():
                    # Calculate total size and last modified time of all videos under this directory
                    total_size, last_modified_time = await run_in_threadpool(
                        get_total_size_and_last_modified_time,
                        get_path_standard_format(entry.path),
                        video_extensions
                    )
                    if total_size > 0:
                        fileBrowse_nodes.append(
                            FileBrowseNode(
                                node = Video.create_new(
                                    id=strawberry.ID(str(ObjectId())),
                                    name=entry.name,
                                    isDir=True,
                                    lastModifyTime=last_modified_time,
                                    size=total_size
                                )
                            )
                        )
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
                    except OSError as e:
                        raise FileBrowseError(f"Error accessing file {entry.path}: {str(e)}")
    except OSError as e:
        raise FileBrowseError(f"Error accessing directory {abs_path}: {str(e)}")


    # 2. Convert the file system entries to FileBrowseNode instances
        # Atthention:
        # 1. For video files, we should check if they are in the database to get their metadata by using their absolute paths, if not, create a new Video instance with basic info 
        # 2. For directories, calculate its total size and the last modified time of all videos under it
    # 3. Return the list of FileBrowseNode instances