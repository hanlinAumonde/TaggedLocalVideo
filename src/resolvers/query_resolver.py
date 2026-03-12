from functools import lru_cache

import strawberry
from bson import ObjectId
from src.config import get_settings
from src.logger import get_logger
from src.services.browse_file_service import get_browse_file_service
from src.services.dir_metadata_service import get_dir_metadata_service
from src.services.path_convert_service import get_path_service
from src.services.tag_operation_service import get_tag_operation_service
from src.services.thumbnail_service import get_thumbnail_service
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
from src.db.models.Video_model import VideoModel
from src.db.models.VideoTag_model import VideoTagModel
from src.errors import DatabaseOperationError, InputValidationError, VideoNotFoundError

logger = get_logger("query_resolver")

class QueryResolver:

    def __init__(self):
        self.settings = get_settings()
        self.pathHepler = get_path_service()
        self.tagOperationService = get_tag_operation_service()
        self.thumbnailService = get_thumbnail_service()
        self.browseFileService = get_browse_file_service()
        self.dirMetadataService = get_dir_metadata_service()
    
    async def resolve_search_videos(self,input: VideoSearchInput) -> VideoSearchResult:
        """
        Resolve function to search for videos based on various criteria.

        :param input: Filter criteria for searching videos.
        :type input: VideoSearchInput
        :return: Search results for videos.
        :rtype: VideoSearchResult
        """
        try:
            validated_input = input.to_pydantic()
        except Exception as e:
            logger.exception(f"Input validation error: {e}")
            raise InputValidationError(field="VideoSearchInput", issue="Invalid input data for video search")

        settings = get_settings()
        query_filters = {}

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

            async def get_video(video_model: VideoModel):
                if video_model.duration is None or video_model.duration == 0.0:
                    video_path = self.pathHepler.to_mounted_path(video_model.path)
                    duration = await self.thumbnailService.get_video_duration(video_path)
                    video_model.duration = duration
                    await video_model.save()
                return await Video.from_mongoDB(video_model)
            
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

    async def resolve_get_top_tags(self) -> list[VideoTag]:
        """
        Resolve function to retrieve the top video tags.

        :return: List of top video tags.
        :rtype: list[VideoTag]
        """
        limit = self.settings.page_size_default.homepage_tags
        try:
            tag_docs = await self.tagOperationService.get_top_tag_docs(limit)
            return [VideoTag(name=tag.name, count=tag.tag_count) for tag in tag_docs]
        except Exception as e:
            logger.exception(f"Database operation error during get top tags: {e}")
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
        limits = self.settings.suggestion_limit

        try:
            match suggestion_type:
                case SearchField.Tag.value:
                    limit = limits.tag
                    if not keyword:
                        tag_docs = await self.tagOperationService.get_top_tag_docs(limit)
                        return [tag.name for tag in tag_docs]

                    prefix_query = VideoTagModel.find(
                        {"name" : {"$regex": f"^{keyword}", "$options":"i"}}
                    )
                    prefix_matches = await self.tagOperationService.get_top_tag_docs(limit,prefix_query)
                    prefix_matches_names = [tag.name for tag in prefix_matches]

                    if limit - len(prefix_matches_names) > 0:
                        contains_query = VideoTagModel.find(
                            {"name": {"$regex": f".*{keyword}.*", "$options":"i", "$nin": prefix_matches_names}}
                        )
                        contains_matches = await self.tagOperationService.get_top_tag_docs(limit, contains_query)
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
        except Exception as e:
            logger.exception(f"Database operation error during get video by id: {e}")
            raise DatabaseOperationError(operation="get video by id", details=f"videoId-{videoId}")
        
        if not video_model:
            logger.exception(f"Video not found: {videoId}")
            raise VideoNotFoundError(str(videoId))
        return await Video.from_mongoDB(video_model)
    
    async def resolve_browse_directory(self,input: RelativePathInput) -> list[FileBrowseNode]:
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
        
        return await self.browseFileService.get_node_list_in_directory(
            self.pathHepler.get_absolute_resource_path(relativePathInputModel),
            skipCache=relativePathInputModel.skipCache,
            recursiveCalculation=relativePathInputModel.recursiveCalculation
        )

    async def resolve_directory_metadata(self,input: RelativePathInput) -> DirectoryMetadataResult:
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
        
        size, last_update_time = await self.dirMetadataService.calculate_directory_metadata(
            self.pathHepler.get_absolute_resource_path(relativePathInputModel),
            skipCache=True,
            recursiveCalculation=True
        )

        return DirectoryMetadataResult(
            totalSize=size,
            lastModifiedTime=last_update_time
        )

@lru_cache
def get_query_resolver() -> QueryResolver:
    return QueryResolver()