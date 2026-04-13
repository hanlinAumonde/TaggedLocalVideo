from functools import lru_cache
import strawberry
from bson import ObjectId
import time
from src.logger import get_logger
from src.schema.types.fileBrowse_type import VideoMutationResult
from src.schema.types.video_type import UpdateVideoMetadataInput, Video
from src.db.models.Video_model import VideoModel
from src.errors import InputValidationError, VideoNotFoundError, DatabaseOperationError
from src.services.dir_metadata_service import get_dir_metadata_service
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.series_service import get_series_service
from src.services.tag_operation_service import get_tag_operation_service
from src.services.resource_handler.resource_handler_service import get_resource_handler_service

logger = get_logger("mutation_resolver")


class MutationResolver:

    def __init__(self):
        self.tagOperationService = get_tag_operation_service()
        self.dirMetadataService = get_dir_metadata_service()
        self.resourceHandlerService = get_resource_handler_service()
        self.seriesService = get_series_service()

    async def resolve_update_video_metadata(self,input: UpdateVideoMetadataInput) -> VideoMutationResult:
        """
        Resolve function to update the metadata of a video.

        :param input: Input containing the video ID and new metadata.
        :type input: UpdateVideoMetadataInput
        :return: VideoMutationResult contains a success flag and an object of updated video metadata
        :rtype: VideoMutationResult
        """
        try:
            validated_input = input.to_pydantic()
        except Exception as e:
            logger.exception(f"Input validation error: {e}")
            raise InputValidationError(field="UpdateVideoMetadataInput", issue="Invalid input data for updating video metadata")

        try:
            video_model = await VideoModel.get(ObjectId(str(validated_input.videoId)))
            if video_model:
                update_tags: dict[str, tuple[int, bool]] = {}

                old_tags = set(video_model.tags or [])
                new_tags = set(validated_input.tags or [])

                # determine tag changes
                for tag in new_tags - old_tags:
                    update_tags[tag] = (1, True)
                for tag in old_tags - new_tags:
                    update_tags[tag] = (1, False)

                # update fields if provided
                if validated_input.name is not None:
                    video_model.name = validated_input.name
                if validated_input.introduction is not None:
                    video_model.introduction = validated_input.introduction
                if validated_input.author is not None:
                    video_model.author = validated_input.author
                if validated_input.loved is not None:
                    video_model.loved = validated_input.loved

                video_model.tags = validated_input.tags

                # series field: None = no change; clear=True = wipe; otherwise set name/order
                series_name_to_ensure: str | None = None
                if validated_input.series is not None:
                    if validated_input.series.clear:
                        video_model.seriesName = None
                        video_model.seriesOrder = None
                    else:
                        video_model.seriesName = validated_input.series.name
                        video_model.seriesOrder = validated_input.series.order
                        series_name_to_ensure = validated_input.series.name

                await video_model.save()
                await self.tagOperationService.update_tag_counts(update_tags=update_tags)
                if series_name_to_ensure:
                    await self.seriesService.ensure_exists(series_name_to_ensure)

                updated_video = await Video.from_mongoDB(video_model)
                return VideoMutationResult(success=True, video=updated_video)

        except VideoNotFoundError:
            logger.exception(f"Video not found: {validated_input.videoId}")
            raise
        except Exception as e:
            logger.exception(f"Database operation error during update video metadata: {e}")
            raise DatabaseOperationError("update_video_metadata", f"videoId-{validated_input.videoId}")

    async def resolve_record_video_view(self,videoId: strawberry.ID) -> VideoMutationResult:
        """
        Resolve function to record a view for a video.

        :param videoId: The ID of the video to record a view for.
        :type videoId: strawberry.ID
        :return: The video with updated view count.
        :rtype: Video
        """
        try:
            video_model = await VideoModel.get(ObjectId(str(videoId)))
            if not video_model:
                raise VideoNotFoundError(str(videoId))

            video_model.viewCount = (video_model.viewCount or 0) + 1
            video_model.lastViewTime = time.time()

            await video_model.save()

            updated_video = await Video.from_mongoDB(video_model)
            return VideoMutationResult(success=True, video=updated_video)

        except VideoNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Database operation error during record video view: {e}")
            raise DatabaseOperationError("record_video_view", f"videoId-{videoId}")

    async def resolve_delete_video(self,videoId: strawberry.ID) -> VideoMutationResult:
        """
        Resolve function to delete a video by its ID.

        :param videoId: The ID of the video to delete.
        :type videoId: strawberry.ID
        :return: Boolean indicating success or failure of the delete operation.
        :rtype: bool
        """
        try:
            video_model = await VideoModel.get(ObjectId(str(videoId)))
            if not video_model:
                raise VideoNotFoundError(str(videoId))

            old_tags = set(video_model.tags or [])
            video_path = AbsolutePath.from_existing_path(video_model.path, video_model.category)

            await video_model.delete()
            await self.tagOperationService.update_tag_counts(update_tags={tag: (1, False) for tag in old_tags})

            video_FS_path = video_path.FS_format_path()

            handler = self.resourceHandlerService.get_handler(video_model.category)
            handler.delete_file(video_FS_path)

            directory_path = handler.dirname(video_FS_path)
            if directory_path:
                await self.dirMetadataService.update_directory_metadata_forward(
                    AbsolutePath.from_existing_path(directory_path, video_model.category)
                )
                
            return VideoMutationResult(success=True, video=None)

        except VideoNotFoundError:
            logger.exception(f"Video not found: {videoId}")
            raise
        except Exception as e:
            logger.exception(f"Database operation error during delete video: {e}")
            raise DatabaseOperationError("delete_video", f"videoId-{videoId}")
        
@lru_cache
def get_mutation_resolver() -> MutationResolver:
    return MutationResolver()