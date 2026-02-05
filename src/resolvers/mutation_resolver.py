import asyncio
import os
from fastapi.concurrency import run_in_threadpool
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
import strawberry
from bson import ObjectId
import time

from src.logger import get_logger
from src.resolvers.resolver_utils import resolver_utils
from src.resolvers.thumbnail_resolver import get_thumbnail_resolver
from src.schema.types.fileBrowse_type import (
    BatchResultType, 
    DirectoryVideosBatchOperationInput, 
    VideoMutationResult,
    VideosBatchOperationInput, 
    VideosBatchOperationResult
)
from src.schema.types.pydantic_types.batch_operation_type import TagsOperationMappingInputModel
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
            if not video_model:
                raise VideoNotFoundError(str(validated_input.videoId))

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

        except VideoNotFoundError:
            logger.error(f"Video not found: {validated_input.videoId}")
            raise
        except Exception as e:
            logger.error(f"Database operation error during update video metadata: {e}")
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
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            raise InputValidationError(field="VideosBatchOperationInput", issue="Invalid input data for batch updating videos")
        
        success_status, message = await _batch_update(
            videoIDs=validated_input.videoIds,
            fileEntries=None,
            author=validated_input.author, 
            tagsOperation=validated_input.tagsOperation
        )

        return VideosBatchOperationResult(
            resultType = success_status,
            message = message
        )
    
    async def resolve_directory_batch_update(self,input: DirectoryVideosBatchOperationInput) -> VideosBatchOperationResult:
        try:
            validated_input = input.to_pydantic()
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            raise InputValidationError(field="DirectoryVideosBatchOperationInput", issue="Invalid input data for batch updating directory videos")
        
        dir_path = resolver_utils().get_absolute_resource_path(validated_input.relativePath)
        entries = await run_in_threadpool(resolver_utils().get_all_video_entries_in_directory, dir_path)
        
        success_status, message = await _batch_update(
            None,
            entries,
            validated_input.author,
            validated_input.tagsOperation
        )
        
        
        return VideosBatchOperationResult(
            resultType = success_status,    
            message = message
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
        
async def _batch_update(videoIDs: list[str] | None,
                        fileEntries: list[os.DirEntry[str]] | None,
                        author: str | None,
                        tagsOperation: TagsOperationMappingInputModel) -> tuple[BatchResultType, str | None]:
    """
    Batch update videos' metadata based on provided video IDs or paths.
    Uses upsert for path-based queries to create new documents if they don't exist.

    :param videoIDs: List of video IDs to update.
    :param fileEntries: List of file entries to update.
    :param author: New author name to set (if provided).
    :param tagsOperation: Tags operation to append or remove.
    :param findById: If True, treat videos as IDs; if False, treat as paths (with upsert).
    :return: Number of documents modified or upserted.
    """
    if not videoIDs and not fileEntries:
        return 0

    successful_updates = 0
    operations = []
    update_tags: dict[str, tuple[int, bool]] = {}
    no_need_update_flag = False

    def track_tag_change(tags: set[str], is_increment: bool):
        for tag in tags:
            tag_record: tuple[int, bool] | None = update_tags.get(tag)
            update_tags[tag] = (tag_record[0] + 1, is_increment) if tag_record else (1, is_increment)

    async def update_existing_videos_operations(video_models: list[VideoModel], findById: bool):
        for video_model in video_models:
            old_tags = set(video_model.tags or [])
            filter_query = {"_id": video_model.id} if findById else {"path": video_model.path}
            update_query = {}

            if author is not None:
                update_query["author"] = author

            if tagsOperation is not None:
                tags_set = set(tagsOperation.tags)
                if tagsOperation.append:
                    new_tags = old_tags.union(tags_set)
                    track_tag_change(new_tags - old_tags, True)
                else:
                    new_tags = old_tags - tags_set
                    track_tag_change(old_tags.intersection(tags_set), False)

                update_query["tags"] = list(new_tags)

            if video_model.duration is None or video_model.duration == 0.0:
                duration = await get_thumbnail_resolver().get_video_duration(
                    resolver_utils().to_mounted_path(video_model.path)
                )     
                if duration is not None and duration > 0.0:
                    update_query["duration"] = duration

            if update_query:
                operations.append(UpdateOne(filter_query, {"$set": update_query}))
        
        if len(operations) == 0 and len(video_models) > 0:
            nonlocal no_need_update_flag
            no_need_update_flag = True

    try:
        if videoIDs is not None:
            # find by IDs
            video_models = await VideoModel.find_many(
                {"_id": {"$in": [ObjectId(str(vid)) for vid in videoIDs]}}
            ).to_list()
            await update_existing_videos_operations(video_models, findById=True)
        else:
            # find by paths with upsert
            paths = [resolver_utils().to_host_path(fe.path) for fe in fileEntries]
            video_models = await VideoModel.find_many(
                {"path": {"$in": paths}}
            ).to_list()
            existing_paths = {vm.path for vm in video_models}

            # process existing documents
            await update_existing_videos_operations(video_models, findById=False)

            # process new documents in parallel with ffprobe duration extraction
            new_entries = [
                entry for entry in fileEntries
                if resolver_utils().to_host_path(entry.path) not in existing_paths
            ]

            if new_entries:
                new_operations = await asyncio.gather(*[
                    resolver_utils().process_new_video_entry(entry, author, tagsOperation, track_tag_change)
                    for entry in new_entries
                ])
                operations.extend(new_operations)

        if operations:
            result = await VideoModel.get_pymongo_collection().bulk_write(operations)
            successful_updates = result.modified_count + result.upserted_count

            await resolver_utils().update_tag_counts(update_tags=update_tags)

            return (BatchResultType.Success, None) if successful_updates == len(operations) else \
                   (BatchResultType.PartialSuccess, 
                    f"{successful_updates} out of {len(operations)} updates succeeded"
                    ) if successful_updates > 0 else \
                   (BatchResultType.Failure, None)

        elif no_need_update_flag:
            return (BatchResultType.AlreadyUpToDate, None)

    except BulkWriteError as bwe:
        logger.error(f"Bulk write error during bulk write operation: {bwe.details}")
        raise DatabaseOperationError("batch_update", "bulk_write_failure")
    except Exception as e:
        logger.error(f"Error during batch update: {e}")
        raise DatabaseOperationError("batch_update", "general_failure")