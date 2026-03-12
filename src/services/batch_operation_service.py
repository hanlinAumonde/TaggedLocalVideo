import asyncio
from functools import lru_cache
import os
from typing import AsyncGenerator
from bson import ObjectId
from fastapi.concurrency import run_in_threadpool
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from src.db.models.Video_model import VideoModel
from src.errors import DatabaseOperationError, FileBrowseError
from src.logger import get_logger
from src.schema.types.fileBrowse_type import (
    BatchOperationStatus, 
    VideosBatchOperationResult, 
    BatchResultType
)
from src.schema.types.pydantic_types.batch_operation_type import TagsOperationMappingInputModel
from src.services.dir_metadata_service import get_dir_metadata_service
from src.services.path_convert_service import get_path_service
from src.services.tag_operation_service import get_tag_operation_service
from src.services.thumbnail_service import get_thumbnail_service

logger = get_logger("batch_operation_service")

class BatchOperationService:

    def __init__(self):
        self.pathHepler = get_path_service()
        self.dirMetadataService = get_dir_metadata_service()
        self.tagOperationService = get_tag_operation_service()
        self.thumbnailService = get_thumbnail_service()

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
    
    async def batch_delete(self, 
                            dir_path: str,
                            videoIds: list[str],
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
                paths = [self.pathHepler.to_host_path(fe.path) for fe in fileEntries]
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
            
            if dir_path:
                await self.dirMetadataService.update_directory_metadata_forward(dir_path)

            yield self.constructBatchOperationStatus(
                resultType=BatchResultType.Success if (result.deleted_count == len(videoIds) if videoIds else result.deleted_count == len(fileEntries)) else \
                        BatchResultType.PartialSuccess if result.deleted_count > 0 
                        else BatchResultType.Failure,
                message=f"Deleted {result.deleted_count} out of {(len(videoIds) if videoIds else len(fileEntries))} videos" if result.deleted_count > 0 else None
            )

        except FileBrowseError:
            raise 
        except Exception as e:
            logger.exception(f"Error during batch delete: {e}")
            raise DatabaseOperationError("batch_delete", "general_failure")

    async def batch_update(self, videoIDs: list[str] | None,
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
                paths = [self.pathHepler.to_host_path(fe.path) for fe in fileEntries]
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
                    if self.pathHepler.to_host_path(entry.path) not in existing_paths
                ]

                if new_entries:
                    new_operations = await asyncio.gather(*[
                        self._process_new_video_entry(
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

                await self.tagOperationService.update_tag_counts(update_tags=update_tags)

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
            logger.exception(f"Bulk write error during bulk write operation: {bwe.details}")
            raise DatabaseOperationError("batch_update", "bulk_write_failure")
        except Exception as e:
            logger.exception(f"Error during batch update: {e}")
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
                    self.tagOperationService.track_tag_change(update_tags, new_tags - old_tags, True)
                else:
                    new_tags = old_tags - tags_set
                    self.tagOperationService.track_tag_change(update_tags, old_tags.intersection(tags_set), False)
                if new_tags != old_tags:
                    update_query["tags"] = list(new_tags)

            if video_model.duration is None or video_model.duration == 0.0:
                duration = await self.thumbnailService.get_video_duration(
                    self.pathHepler.to_mounted_path(video_model.path)
                )     
                if duration is not None and duration > 0.0:
                    update_query["duration"] = duration

            if update_query:
                operations.append(UpdateOne(filter_query, {"$set": update_query}))
        
        if len(operations) == 0 and len(video_models) > 0:
            no_need_update_flag = True

        return no_need_update_flag
    
    async def _remove_videos_and_update_tags(self, actually_deleted: list[VideoModel]):
        paths_to_delete = [self.pathHepler.to_mounted_path(v.path) for v in actually_deleted]
        await run_in_threadpool(self._remove_videos_by_paths, paths_to_delete)

        update_tags: dict[str, tuple[int, bool]] = {}
        for video in actually_deleted:
            self.tagOperationService.track_tag_change(update_tags, set(video.tags or []), False)
        if update_tags:
            await self.tagOperationService.update_tag_counts(update_tags=update_tags)
    
    def _remove_videos_by_paths(self, paths: list[str]):
        try:
            for path in paths:
                os.remove(self.pathHepler.to_mounted_path(path))
        except Exception as e:
            logger.exception(f"Error removing video files: {e}")
            raise FileBrowseError("Error removing video files.")
        
    async def _process_new_video_entry(
        self,
        entry: os.DirEntry[str],
        author: str | None,
        tagsOperation: TagsOperationMappingInputModel | None,
        update_tags: dict[str, tuple[int,bool]]
    ) -> UpdateOne:
        """
        Process a single new video entry: get duration via ffprobe and build upsert operation.

        :param entry: Directory entry for the video file
        :param author: Author name to set (if provided)
        :param tagsOperation: Tags operation to apply
        :param track_tag_change: Callback to track tag changes
        :return: UpdateOne operation for bulk write
        """
        host_path = self.pathHepler.to_host_path(entry.path)
        filter_query = {"path": host_path}

        # Get video duration with semaphore to limit concurrent ffprobe processes
        duration = await self.thumbnailService.get_video_duration(entry.path) or 0.0

        stat = entry.stat()
        set_on_insert = VideoModel(
            name=entry.name,
            path=host_path,
            isDir=False,
            lastModifyTime=stat.st_mtime,
            size=stat.st_size,
            duration=duration,
            tags=[]
        ).model_dump()

        if author is not None:
            set_on_insert["author"] = author

        if tagsOperation is not None:
            tags_set = set(tagsOperation.tags)
            if tagsOperation.append:
                set_on_insert["tags"] = list(tags_set)
                self.tagOperationService.track_tag_change(update_tags, tags_set, True)

        return UpdateOne(filter_query, {"$setOnInsert": set_on_insert}, upsert=True)

@lru_cache
def get_batch_operation_service() -> BatchOperationService:
    BatchOperationService()