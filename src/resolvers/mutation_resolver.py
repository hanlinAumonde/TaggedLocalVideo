import os
import strawberry
from bson import ObjectId
import time

from src.logger import get_logger
from src.resolvers.resolver_utils import resolver_utils
from src.schema.types.fileBrowse_type import VideoMutationResult

from src.schema.types.video_type import UpdateVideoMetadataInput, Video
from src.db.models.Video_model import VideoModel
from src.errors import InputValidationError, VideoNotFoundError, DatabaseOperationError

logger = get_logger("mutation_resolver")


class MutationResolver:

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
            logger.error(f"Input validation error: {e}")
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

                await video_model.save()
                await resolver_utils().update_tag_counts(update_tags=update_tags)

                updated_video = await Video.from_mongoDB(video_model)
                return VideoMutationResult(success=True, video=updated_video)
            
            else:
                if not validated_input.path:
                    raise VideoNotFoundError(str(validated_input.videoId))

        except VideoNotFoundError:
            logger.error(f"Video not found: {validated_input.videoId}")
            raise
        except Exception as e:
            logger.error(f"Database operation error during update video metadata: {e}")
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
            logger.error(f"Database operation error during record video view: {e}")
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
            video_path = video_model.path

            await video_model.delete()
            await resolver_utils().update_tag_counts(update_tags={tag: (1, False) for tag in old_tags})

            os.remove(resolver_utils().to_mounted_path(video_path))
            logger.info(f"Deleted video file at path: {video_path}")

            return VideoMutationResult(success=True, video=None)

        except VideoNotFoundError:
            logger.error(f"Video not found: {videoId}")
            raise
        except Exception as e:
            logger.error(f"Database operation error during delete video: {e}")
            raise DatabaseOperationError("delete_video", f"videoId-{videoId}")