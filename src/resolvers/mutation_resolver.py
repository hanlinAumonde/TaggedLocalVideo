import strawberry

from src.context import ContextEnum, get_context_value
from src.errors import InputValidationError
from src.logger import get_logger
from src.schema.types.fileBrowse_type import VideoMutationResult
from src.schema.types.video_type import UpdateVideoMetadataInput, Video
from src.features.catalog.catalog_service import CatalogService

logger = get_logger("mutation_resolver")


async def resolve_update_video_metadata(input: UpdateVideoMetadataInput, info: strawberry.Info) -> VideoMutationResult:
    """
    Resolve function to update the metadata of a video.

    :param input: Input containing the video ID and new metadata.
    :type input: UpdateVideoMetadataInput
    :param info: Strawberry GraphQL info object.
    :type info: strawberry.Info
    :return: VideoMutationResult containing a success flag and the updated video.
    :rtype: VideoMutationResult
    """
    try:
        validated_input = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="UpdateVideoMetadataInput", issue="Invalid input data for updating video metadata")

    catalogService: CatalogService = get_context_value(info, ContextEnum.CATALOG_SERVICE)
    video_model = await catalogService.update_metadata(validated_input)
    return VideoMutationResult(success=True, video=await Video.from_mongoDB(video_model))


async def resolve_record_video_view(videoId: strawberry.ID, info: strawberry.Info) -> VideoMutationResult:
    """
    Resolve function to record a view for a video.

    :param videoId: The ID of the video to record a view for.
    :type videoId: strawberry.ID
    :param info: Strawberry GraphQL info object.
    :type info: strawberry.Info
    :return: VideoMutationResult containing the video with its updated view count.
    :rtype: VideoMutationResult
    """
    catalogService: CatalogService = get_context_value(info, ContextEnum.CATALOG_SERVICE)
    video_model = await catalogService.record_view(str(videoId))
    return VideoMutationResult(success=True, video=await Video.from_mongoDB(video_model))


async def resolve_delete_video(videoId: strawberry.ID, info: strawberry.Info) -> VideoMutationResult:
    """
    Resolve function to delete a video by its ID.

    :param videoId: The ID of the video to delete.
    :type videoId: strawberry.ID
    :param info: Strawberry GraphQL info object.
    :type info: strawberry.Info
    :return: VideoMutationResult flagging success; no video is returned, it is gone.
    :rtype: VideoMutationResult
    """
    catalogService: CatalogService = get_context_value(info, ContextEnum.CATALOG_SERVICE)
    await catalogService.delete_video(str(videoId))
    return VideoMutationResult(success=True, video=None)
