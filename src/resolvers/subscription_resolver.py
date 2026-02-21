import asyncio
from functools import lru_cache
import os
from typing import AsyncGenerator
from bson import ObjectId
from fastapi.concurrency import run_in_threadpool
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from src.db.models.Video_model import VideoModel
from src.errors import DatabaseOperationError, FileBrowseError, InputValidationError
from src.logger import get_logger
from src.resolvers.resolver_utils import resolver_utils
from src.resolvers.thumbnail_resolver import get_thumbnail_resolver
from src.schema.types.fileBrowse_type import BatchOperationStatus, BatchResultType, DirectoryVideosBatchOperationInput, VideosBatchOperationInput, VideosBatchOperationResult
from src.schema.types.pydantic_types.batch_operation_type import TagsOperationMappingInputModel


logger = get_logger("SubscriptionResolver")

class SubscriptionResolver:

    def constructBatchOperationStatus(self, resultType: BatchResultType | None = None, 
                                   message: str | None = None, 
                                   status: str | None = None) -> BatchOperationStatus:
        if resultType is None or message is None:
            return BatchOperationStatus(
                result=None,
                status=status
            )
        return BatchOperationStatus(
            result=VideosBatchOperationResult(
                resultType=resultType,
                message=message
            ),
            status=status
        )

    async def resolve_batch_operations(self,
                                       input: VideosBatchOperationInput,
                                       update: bool) -> AsyncGenerator[BatchOperationStatus, None]:
        """
        Resolve function to batch update tags for multiple videos.

        :param input: Input containing the mapping of video IDs to tags and the operation type (append/remove).
        :type input: VideosBatchOperationInput
        :return: An asynchronous generator yielding the status of the batch update operation.
        :rtype: AsyncGenerator[BatchOperationStatus, None]
        """
        try:
            validated_input = input.to_pydantic()
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            raise InputValidationError(field="VideosBatchOperationInput", issue="Invalid input data for batch updating videos")
        
        if update:
            async for status in self._batch_update(
                videoIDs=validated_input.videoIds,
                fileEntries=None,
                author=validated_input.author, 
                tagsOperation=validated_input.tagsOperation,
            ):
                yield status
        else:
            async for status in self._batch_delete(
                videoIds=validated_input.videoIds,
                fileEntries=None
            ):
                yield status

    async def resolve_directory_batch_operations(self, 
                                                 input: DirectoryVideosBatchOperationInput,
                                                 update: bool) -> AsyncGenerator[BatchOperationStatus, None]:
        """
        Resolve function to batch update tags for videos in a specified directory.
        
        :param input: Input containing the relative path of the directory and tags operation details.
        :type input: DirectoryVideosBatchOperationInput
        :return: An asynchronous generator yielding the status of the batch update operation.
        :rtype: AsyncGenerator[BatchOperationStatus, None]
        """
        try:
            validated_input = input.to_pydantic()
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            raise InputValidationError(field="DirectoryVideosBatchOperationInput", issue="Invalid input data for batch updating directory videos")
        
        dir_path = resolver_utils().get_absolute_resource_path(validated_input.relativePath)
        entries = await run_in_threadpool(resolver_utils().get_all_video_entries_in_directory, dir_path)

        yield self.constructBatchOperationStatus(
            status=f"Found {len(entries)} video entries in directory '{validated_input.relativePath.relativePath}' for batch update"
        )
        
        if update:
            async for status in self._batch_update(
                None,
                entries,
                validated_input.author,
                validated_input.tagsOperation
            ):
                yield status
        else:
            async for status in self._batch_delete(None, entries):
                yield status

    async def _batch_delete(self, videoIds: list[str],
                            fileEntries: list[os.DirEntry[str]] | None) -> AsyncGenerator[BatchOperationStatus, None]:
        """
        Batch delete videos based on provided video IDs or paths.

        :param videoIds: List of video IDs to delete.
        :param fileEntries: List of file entries to delete.
        :return: Number of documents deleted.
        """
        if not videoIds and not fileEntries:
            yield self.constructBatchOperationStatus(
                resultType=BatchResultType.Failure,
                message="No video IDs or file entries provided for batch delete"
            )
        
        try:
            if videoIds is not None:
                videos = await VideoModel.find_many(
                    {"_id": {"$in": [ObjectId(str(vid)) for vid in videoIds]}}
                ).to_list()
                # delete by IDs
                result = await VideoModel.get_pymongo_collection().delete_many(
                    {"_id": {"$in": [ObjectId(str(vid)) for vid in videoIds]}}
                )
                yield self.constructBatchOperationStatus(
                    status=f"Deleted {result.deleted_count} videos based on IDs"
                )
                videos_not_deleted = await VideoModel.find_many(
                    {"_id": {"$in": [ObjectId(str(vid)) for vid in videoIds]}}
                ).to_list()
                not_deleted_ids = {v.id for v in videos_not_deleted}
                actually_deleted = [v for v in videos if v.id not in not_deleted_ids]
                await self._remove_videos_and_update_tags(actually_deleted)

            else:
                # delete by paths
                paths = [resolver_utils().to_host_path(fe.path) for fe in fileEntries]
                videos_before_delete = await VideoModel.find_many(
                    {"path": {"$in": paths}}
                ).to_list()
                result = await VideoModel.get_pymongo_collection().delete_many(
                    {"path": {"$in": paths}}
                )
                yield self.constructBatchOperationStatus(
                    status=f"Deleted {result.deleted_count} videos based on paths"
                )
                videos_not_deleted = await VideoModel.find_many(
                    {"path": {"$in": paths}}
                ).to_list()
                not_deleted_paths = {v.path for v in videos_not_deleted}
                actually_deleted = [v for v in videos_before_delete if v.path not in not_deleted_paths]
                await self._remove_videos_and_update_tags(actually_deleted)
            
            yield self.constructBatchOperationStatus(
                resultType=BatchResultType.Success if (result.deleted_count == len(videoIds) if videoIds else result.deleted_count == len(fileEntries)) else \
                        BatchResultType.PartialSuccess if result.deleted_count > 0 
                        else BatchResultType.Failure,
                message=f"Deleted {result.deleted_count} out of {(len(videoIds) if videoIds else len(fileEntries))} videos" if result.deleted_count > 0 else None
            )

        except FileBrowseError:
            raise 
        except Exception as e:
            logger.error(f"Error during batch delete: {e}")
            raise DatabaseOperationError("batch_delete", "general_failure")

    async def _batch_update(self, videoIDs: list[str] | None,
                            fileEntries: list[os.DirEntry[str]] | None,
                            author: str | None,
                            tagsOperation: TagsOperationMappingInputModel) -> AsyncGenerator[BatchOperationStatus, None]:
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
            yield self.constructBatchOperationStatus(
                resultType=BatchResultType.Failure,
                message="No video IDs or file entries provided for batch update"
            )

        successful_updates = 0
        operations = []
        update_tags: dict[str, tuple[int, bool]] = {}
        no_need_update_flag = False

        try:
            if videoIDs is not None:
                # find by IDs
                video_models = await VideoModel.find_many(
                    {"_id": {"$in": [ObjectId(str(vid)) for vid in videoIDs]}}
                ).to_list()
                no_need_update_flag = await self._update_existing_videos_operations(
                    video_models, 
                    findById=True, 
                    author=author, 
                    tagsOperation=tagsOperation, 
                    update_tags=update_tags, 
                    operations=operations, 
                    no_need_update_flag=no_need_update_flag
                )
                yield self.constructBatchOperationStatus(
                    status=f"Prepared update operations for {len(video_models)} existing videos based on IDs"
                )

            else:
                # find by paths with upsert
                paths = [resolver_utils().to_host_path(fe.path) for fe in fileEntries]
                video_models = await VideoModel.find_many(
                    {"path": {"$in": paths}}
                ).to_list()
                existing_paths = {vm.path for vm in video_models}

                # process existing documents
                no_need_update_flag = await self._update_existing_videos_operations(
                    video_models, 
                    findById=False, 
                    author=author, 
                    tagsOperation=tagsOperation, 
                    update_tags=update_tags, 
                    operations=operations, 
                    no_need_update_flag=no_need_update_flag
                )

                # process new documents in parallel with ffprobe duration extraction
                new_entries = [
                    entry for entry in fileEntries
                    if resolver_utils().to_host_path(entry.path) not in existing_paths
                ]

                if new_entries:
                    new_operations = await asyncio.gather(*[
                        resolver_utils().process_new_video_entry(
                            entry=entry, 
                            author=author, 
                            tagsOperation=tagsOperation, 
                            update_tags=update_tags,
                        )
                        for entry in new_entries
                    ])
                    operations.extend(new_operations)
                    yield self.constructBatchOperationStatus(
                        status=f"Prepared update operations for {len(video_models)} existing videos and {len(new_entries)} new videos based on paths"
                    )

            if operations:
                result = await VideoModel.get_pymongo_collection().bulk_write(operations)
                successful_updates = result.modified_count + result.upserted_count

                yield self.constructBatchOperationStatus(
                    status=f"Executed batch update operations: {result.modified_count} modified, {result.upserted_count} upserted"
                )

                await resolver_utils().update_tag_counts(update_tags=update_tags)

                yield self.constructBatchOperationStatus(
                    resultType=BatchResultType.Success if successful_updates == len(operations) else \
                            BatchResultType.PartialSuccess if successful_updates > 0 else \
                            BatchResultType.Failure,
                    message=f"{successful_updates} out of {len(operations)} updates succeeded" if successful_updates > 0 else None
                )
            elif no_need_update_flag:
                yield self.constructBatchOperationStatus(
                    resultType=BatchResultType.AlreadyUpToDate,
                    message="All videos are already up to date, no updates needed"
                )

        except BulkWriteError as bwe:
            logger.error(f"Bulk write error during bulk write operation: {bwe.details}")
            raise DatabaseOperationError("batch_update", "bulk_write_failure")
        except Exception as e:
            logger.error(f"Error during batch update: {e}")
            raise DatabaseOperationError("batch_update", "general_failure")

    async def _update_existing_videos_operations(self, video_models: list[VideoModel], 
                                                findById: bool,
                                                author: str | None,
                                                tagsOperation: TagsOperationMappingInputModel,
                                                operations: list[UpdateOne],
                                                no_need_update_flag: bool,
                                                update_tags: dict[str, tuple[int, bool]]):
        for video_model in video_models:
            old_tags = set(video_model.tags or [])
            filter_query = {"_id": video_model.id} if findById else {"path": video_model.path}
            update_query = {}

            if author is not None and video_model.author != author:
                update_query["author"] = author

            if tagsOperation is not None:
                tags_set = set(tagsOperation.tags)
                if tagsOperation.append:
                    new_tags = old_tags.union(tags_set)
                    resolver_utils()._track_tag_change(update_tags, new_tags - old_tags, True)
                else:
                    new_tags = old_tags - tags_set
                    resolver_utils()._track_tag_change(update_tags, old_tags.intersection(tags_set), False)
                if new_tags != old_tags:
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
            no_need_update_flag = True

        return no_need_update_flag
    
    async def _remove_videos_and_update_tags(self, actually_deleted: list[VideoModel]):
        paths_to_delete = [resolver_utils().to_mounted_path(v.path) for v in actually_deleted]
        await run_in_threadpool(resolver_utils().remove_videos_by_paths, paths_to_delete)

        update_tags: dict[str, tuple[int, bool]] = {}
        for video in actually_deleted:
            resolver_utils()._track_tag_change(update_tags, set(video.tags or []), False)
        if update_tags:
            await resolver_utils().update_tag_counts(update_tags=update_tags)

@lru_cache()
def get_subscription_resolver() -> SubscriptionResolver:
    return SubscriptionResolver()