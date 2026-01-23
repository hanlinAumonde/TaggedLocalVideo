import os
import strawberry
from bson import ObjectId
import time

from src.resolvers.resolver_utils import resolver_utils
from src.schema.types.fileBrowse_type import VideoMutationResult, VideosBatchOperationInput, VideosBatchOperationResult
from src.schema.types.video_type import UpdateVideoMetadataInput, Video
from src.db.models.Video_model import VideoModel, VideoTagModel
from src.errors import InputValidationError, VideoNotFoundError, DatabaseOperationError

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
        except Exception:
            raise InputValidationError(field="UpdateVideoMetadataInput", issue="Invalid input data for updating video metadata")

        try:
            video_model = await VideoModel.get(ObjectId(str(validated_input.videoId)))
            if not video_model:
                raise VideoNotFoundError(str(validated_input.videoId))

            old_tags = set(video_model.tags or [])
            new_tags = set(validated_input.tags)

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
            await _update_tag_counts(old_tags, new_tags)

            updated_video = await Video.from_mongoDB(video_model)
            return VideoMutationResult(success=True, video=updated_video)

        except VideoNotFoundError:
            raise
        except Exception:
            raise DatabaseOperationError("update_video_metadata", f"videoId-{validated_input.videoId}")

    async def resolve_batch_update(self,input: VideosBatchOperationInput) -> VideosBatchOperationResult:
        """
        Resolve function to batch update tags for multiple videos.

        :param input: Input containing the mapping of video IDs to tags and the operation type (append/remove).
        :type input: VideosBatchOperationInput
        :return: Result of the batch update operation.
        :rtype: VideosBatchOperationResult
        """
        try:
            validated_input = input.to_pydantic()
        except Exception:
            raise InputValidationError(field="VideosBatchOperationInput", issue="Invalid input data for batch updating videos")

        successful_updates = []

        for video_id_str in validated_input.videoIds:
            try:
                video_model = await VideoModel.get(ObjectId(str(video_id_str)))
                if not video_model:
                    continue

                # Update Author if provided
                if validated_input.author is not None:
                    video_model.author = validated_input.author

                # Update Tags if operation provided
                if validated_input.tagsOperation is not None:
                    old_tags = set(video_model.tags or [])
                    tags_to_update = set(validated_input.tagsOperation.tags)

                    if validated_input.tagsOperation.append:
                        new_tags = old_tags.union(tags_to_update)
                    else:
                        new_tags = old_tags - tags_to_update

                    video_model.tags = list(new_tags)
                    await _update_tag_counts(old_tags, new_tags)

                await video_model.save()
                successful_updates.append(video_id_str)

            except Exception:
                continue # skip failures for individual videos
        
        return VideosBatchOperationResult(
            success = len(successful_updates) > 0,
            successfulUpdatesMappings = successful_updates
        )

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
        except Exception:
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

            await _update_tag_counts(old_tags, set())

            os.remove(resolver_utils().to_mounted_path(video_path))

            return VideoMutationResult(success=True, video=None)

        except VideoNotFoundError:
            raise
        except Exception:
            raise DatabaseOperationError("delete_video", f"videoId-{videoId}")
        

async def _update_tag_counts(old_tags: set[str], new_tags: set[str]) -> None:
    """
    update the tag counts in the database based on the changes in tags.

    :param old_tags: Set of old tag names.
    :param new_tags: Set of new tag names.
    :type old_tags: set[str]
    :type new_tags: set[str]
    :return: None
    :rtype: None
    """
    tags_to_increment = new_tags - old_tags
    tags_to_decrement = old_tags - new_tags

    for tag_name in tags_to_increment:
        tag_model = await VideoTagModel.find_one({"name": tag_name})
        if tag_model:
            tag_model.tag_count += 1
            await tag_model.save()
        else:
            new_tag = VideoTagModel(name=tag_name, tag_count=1)
            await new_tag.insert()

    for tag_name in tags_to_decrement:
        tag_model = await VideoTagModel.find_one({"name": tag_name})
        if tag_model:
            tag_model.tag_count = max(0, tag_model.tag_count - 1)
            if tag_model.tag_count == 0:
                await tag_model.delete()
            else:
                await tag_model.save()