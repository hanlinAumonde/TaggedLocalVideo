import strawberry
from bson import ObjectId

from src.config import Settings
from src.context import ContextEnum, get_context_value
from src.db.models.Video_model import VideoModel
from src.db.models.VideoTag_model import VideoTagModel
from src.errors import DatabaseOperationError, InputValidationError, VideoNotFoundError
from src.logger import get_logger
from src.schema.types.fileBrowse_type import FileBrowseNode, RelativePathInput
from src.schema.types.search_type import (
    DirectoryMetadataResult,
    SearchFrom,
    SuggestionInput,
    VideoSearchInput,
    VideoSearchResult,
    VideoSortOption,
    SearchField,
    Pagination
)
from src.schema.types.video_type import Video, VideoTag
from src.services.browse_file_service import BrowseFileService
from src.services.dir_metadata_service import DirMetadataService
from src.services.ffmpeg_service import FFmpegService
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.resource_handler_service import ResourceHandlerService
from src.services.series_service import SeriesService
from src.services.tag_operation_service import TagOperationService
from src.services.tasks.migration_service import find_locked_paths
from src.services.thumbnail_service import ThumbnailService

logger = get_logger("query_resolver")

#class QueryResolver:
    
async def resolve_search_videos(input: VideoSearchInput, info: strawberry.Info) -> VideoSearchResult:
    """
    Resolve function to search for videos based on various criteria.

    :param input: Filter criteria for searching videos.
    :type input: VideoSearchInput
    :param info: Strawberry GraphQL info object.
    :type info: strawberry.Info
    :return: Search results for videos.
    :rtype: VideoSearchResult
    """
    try:
        validated_input = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="VideoSearchInput", issue="Invalid input data for video search")

    query_filters = {}

    # Exclude videos from categories not in current config
    settings: Settings = get_context_value(info, ContextEnum.SETTINGS)
    valid_categories = settings.get_valid_categories()
    if len(valid_categories) == 0:
        return VideoSearchResult(
            pagination=Pagination(
                size=0,totalCount=0,currentPageNumber=1
            ),
            videos=[]
        )
    if valid_categories:
        query_filters["category"] = {"$in": valid_categories}

    # build query
    if validated_input.titleKeyword.keyWord:
        query_filters["name"] = {"$regex": validated_input.titleKeyword.keyWord, "$options": "i"}
    if validated_input.author.keyWord:
        query_filters["author"] = {"$regex": validated_input.author.keyWord, "$options": "i"}
    if validated_input.tags:
        query_filters["tags"] = {"$all": validated_input.tags}
    if validated_input.sortBy == VideoSortOption.Loved.value:
        query_filters["loved"] = True

    sort_mapping = {
        VideoSortOption.Latest.value: [("lastViewTime", -1)],
        VideoSortOption.MostViewed.value: [("viewCount", -1), ("lastViewTime", -1)],
        VideoSortOption.Loved.value: [("loved", -1), ("lastViewTime", -1)],
        VideoSortOption.Longest.value: [("duration", -1)],
    }
    sort_criteria = sort_mapping.get(validated_input.sortBy, [("lastModifyTime", -1)])

    if validated_input.fromPage == SearchFrom.FrontalPage.value:
        page_size = settings.page_size_default.homepage_videos
    else:
        page_size = settings.page_size_default.searchpage
    page_number = validated_input.currentPageNumber or 1
    skip = (page_number - 1) * page_size

    try:
        # execute query
        query = VideoModel.find(query_filters)
        total_count = await query.count()
        video_models = await query.sort(sort_criteria).skip(skip).limit(page_size).to_list()

        # One lookup for the whole page rather than one per video.
        locked_paths = await find_locked_paths(vm.path for vm in video_models)

        async def get_video(video_model: VideoModel, info: strawberry.Info = info) -> Video:
            handlerService: ResourceHandlerService = get_context_value(info, ContextEnum.RESOURCE_HANDLER_SERVICE)
            ffmpegService: FFmpegService = get_context_value(info, ContextEnum.FFMPEG_SERVICE)

            if video_model.duration is None or video_model.duration == 0.0:
                handler = handlerService.get_handler(video_model.category)
                video_path = AbsolutePath.from_existing_path(
                    path=video_model.path,
                    category=video_model.category,
                    handler=handler
                ).FS_format_path()
                duration = await ffmpegService.get_video_duration(handler, video_path)
                video_model.duration = duration
                await video_model.save()
            return await Video.from_mongoDB(
                video_model, isLocked=video_model.path in locked_paths
            )

        # build results
        videos = [await get_video(vm) for vm in video_models]
        pagination = Pagination(
            size=page_size,
            totalCount=total_count,
            currentPageNumber=page_number
        )

        return VideoSearchResult(pagination=pagination, videos=videos)
    
    except Exception as e:
        logger.exception(f"Database operation error during video search: {e}")
        raise DatabaseOperationError(operation="video search", 
                                        details=f"Filters-{query_filters}, Sort-{sort_criteria}, Skip-{skip}, Limit-{page_size}")

async def resolve_get_top_tags(info: strawberry.Info) -> list[VideoTag]:
    """
    Resolve function to retrieve the top video tags.

    :return: List of top video tags.
    :rtype: list[VideoTag]
    """
    settings: Settings = get_context_value(info, ContextEnum.SETTINGS)
    tagOperationService: TagOperationService = get_context_value(info, ContextEnum.TAG_OPERATION_SERVICE)
    limit = settings.page_size_default.homepage_tags
    try:
        tag_docs = await tagOperationService.get_top_tag_docs(limit)
        return [VideoTag(name=tag.name, count=tag.tag_count) for tag in tag_docs]
    except Exception as e:
        logger.exception(f"Database operation error during get top tags: {e}")
        raise DatabaseOperationError(operation="get top tags",
                                        details=f"Limit-{limit}")

async def resolve_get_suggestions(input: SuggestionInput, info: strawberry.Info) -> list[str]:
    """
    Resolve function to get suggestions based on a keyword and suggestion type.

    :param input: Input containing the keyword and suggestion type.
    :type input: SuggestionInput
    :return: Suggestion results.
    :rtype: SuggestionResults
    """
    try:             
        validated_input = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="SuggestionInput", issue="Invalid input data for suggestions")

    if validated_input.keyword.keyWord:
        keyword = validated_input.keyword.keyWord
    else:
        return []
    suggestion_type = validated_input.suggestionType
    settings: Settings = get_context_value(info, ContextEnum.SETTINGS)
    tagOperationService: TagOperationService = get_context_value(info, ContextEnum.TAG_OPERATION_SERVICE)
    limits = settings.suggestion_limit

    try:
        match suggestion_type:
            case SearchField.Tag.value:
                limit = limits.tag
                if not keyword:
                    tag_docs = await tagOperationService.get_top_tag_docs(limit)
                    return [tag.name for tag in tag_docs]

                prefix_query = VideoTagModel.find(
                    {"name" : {"$regex": f"^{keyword}", "$options":"i"}}
                )
                prefix_matches = await tagOperationService.get_top_tag_docs(limit,prefix_query)
                prefix_matches_names = [tag.name for tag in prefix_matches]

                if limit - len(prefix_matches_names) > 0:
                    contains_query = VideoTagModel.find(
                        {"name": {"$regex": f".*{keyword}.*", "$options":"i", "$nin": prefix_matches_names}}
                    )
                    contains_matches = await tagOperationService.get_top_tag_docs(limit, contains_query)
                    prefix_matches_names.extend([tag.name for tag in contains_matches])

                return prefix_matches_names

            case _:
                limit = limits.name if suggestion_type == SearchField.Name.value else limits.author
                pipeline = [
                    {"$match": {suggestion_type.lower(): {"$regex": keyword, "$options": "i"}}},
                    {"$group": {"_id": "$" + suggestion_type.lower()}},
                    {"$limit": limit}
                ]
                
                collection = VideoModel.get_pymongo_collection()
                cursor = await collection.aggregate(pipeline)
                result = []
                async for doc in cursor:
                    if doc.get("_id"):
                        result.append(doc["_id"])
                return result
    except Exception as e:
        logger.exception(f"Database operation error during get suggestions: {e}")
        raise DatabaseOperationError(operation="get suggestions",
                                        details=f"Keyword-{keyword}, SuggestionType-{suggestion_type}")

    return []

async def resolve_get_video_by_id(videoId: strawberry.ID) -> Video:
    """
    Resolve function to retrieve a video by its ID.

    :param videoId: The ID of the video to retrieve.
    :type videoId: strawberry.ID
    :return: The video corresponding to the given ID.
    :rtype: Video
    """
    try:
        video_model = await VideoModel.get(ObjectId(str(videoId)))
    except Exception as e:
        logger.exception(f"Database operation error during get video by id: {e}")
        raise DatabaseOperationError(operation="get video by id", details=f"videoId-{videoId}")
    
    if not video_model:
        logger.exception(f"Video not found: {videoId}")
        raise VideoNotFoundError(str(videoId))

    # Returned rather than refused: the player page needs the metadata in order to show
    # why playback is unavailable.
    locked_paths = await find_locked_paths([video_model.path])
    return await Video.from_mongoDB(
        video_model, isLocked=video_model.path in locked_paths
    )

async def resolve_browse_directory(input: RelativePathInput, info: strawberry.Info) -> list[FileBrowseNode]:
    """
    Resolve function to browse videos in a directory specified by a relative path.

    :param input: The relative path input to browse.
    :type input: RelativePathInput
    :return: List of file browse nodes in the specified directory.
    :rtype: list[FileBrowseNode]
    """
    try:
        relativePathInputModel = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="RelativePathInput", issue="Invalid input data for directory browsing")
    
    browseFileService: BrowseFileService = get_context_value(info, ContextEnum.BROWSE_FILE_SERVICE)
    return await browseFileService.get_node_list_in_directory(
        AbsolutePath.from_relative_path(
            parsedPath=relativePathInputModel.parsedPath,
            handlerService=get_context_value(info, ContextEnum.RESOURCE_HANDLER_SERVICE),
            settings=get_context_value(info, ContextEnum.SETTINGS)
        ),
        skipCache=relativePathInputModel.skipCache,
        recursiveCalculation=relativePathInputModel.recursiveCalculation
    )

async def resolve_search_series_by_prefix(prefix: str, limit: int, info: strawberry.Info) -> list[str]:
    """
    Resolve function to look up series names by prefix (case-insensitive). Used for the
    autocomplete dropdown in the video edit panel.

    :param prefix: The prefix to search for.
    :type prefix: str
    :param limit: The maximum number of series names to return.
    :type limit: int
    :return: List of series names matching the prefix.
    :rtype: list[str]
    """
    if limit <= 0:
        return []
    try:
        seriesService: SeriesService = get_context_value(info, ContextEnum.SERIES_SERVICE)
        return await seriesService.search_by_prefix(prefix or "", limit)
    except Exception as e:
        logger.exception(f"Database operation error during search series by prefix: {e}")
        raise DatabaseOperationError(operation="search series by prefix",
                                        details=f"Prefix-{prefix}, Limit-{limit}")

async def resolve_get_series_videos(name: str, info: strawberry.Info) -> list[Video]:
    """
    Resolve function to retrieve all videos belonging to a series, ordered by seriesOrder
    ascending. Videos outside the currently configured categories are excluded.

    :param name: The name of the series to retrieve videos for.
    :type name: str
    :return: List of videos in the specified series.
    :rtype: list[Video]
    """
    if not name:
        return []
    try:
        settings: Settings = get_context_value(info, ContextEnum.SETTINGS)
        seriesService: SeriesService = get_context_value(info, ContextEnum.SERIES_SERVICE)
        valid_categories = settings.get_valid_categories()
        video_models = await seriesService.get_videos_in_series(name, valid_categories)
        locked_paths = await find_locked_paths(vm.path for vm in video_models)
        return [
            await Video.from_mongoDB(vm, isLocked=vm.path in locked_paths)
            for vm in video_models
        ]
    except Exception as e:
        logger.exception(f"Database operation error during get series videos: {e}")
        raise DatabaseOperationError(operation="get series videos", details=f"Name-{name}")

async def resolve_directory_metadata(input: RelativePathInput, info: strawberry.Info) -> DirectoryMetadataResult:
    """
    Resolve function to get metadata of a directory specified by a relative path.

    :param input: The relative path input of the directory.
    :type input: RelativePathInput
    :return: Directory metadata result containing total size and last modified time.
    :rtype: DirectoryMetadataResult
    """
    try:
        relativePathInputModel = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="RelativePathInput", issue="Invalid input data for directory metadata")
    
    abs_path = AbsolutePath.from_relative_path(
        parsedPath=relativePathInputModel.parsedPath,
        handlerService=get_context_value(info, ContextEnum.RESOURCE_HANDLER_SERVICE),
        settings=get_context_value(info, ContextEnum.SETTINGS)
    )
    if abs_path.is_root_level() or abs_path.is_category_level():
        return DirectoryMetadataResult(
            totalSize=0.0,
            lastModifiedTime=0.0
        )
    dirMetadataService: DirMetadataService = get_context_value(info, ContextEnum.DIR_METADATA_SERVICE)
    size, last_update_time = await dirMetadataService.calculate_directory_metadata(
        abs_path,
        skipCache=True,
        recursiveCalculation=True
    )

    return DirectoryMetadataResult(
        totalSize=size,
        lastModifiedTime=last_update_time
    )