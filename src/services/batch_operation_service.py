import asyncio
from functools import lru_cache
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
from src.services.path_convert_service import AbsolutePath
from src.services.resource_handler.base_file_entry import BaseFileEntry
from src.services.resource_handler.resource_handler_service import get_resource_handler_service
from src.services.tag_operation_service import get_tag_operation_service
from src.services.thumbnail_service import get_thumbnail_service

logger = get_logger("batch_operation_service")

class BatchOperationService:

    def __init__(self):
        self.dirMetadataService = get_dir_metadata_service()
        self.tagOperationService = get_tag_operation_service()
        self.thumbnailService = get_thumbnail_service()
        self.resourceHandlerService = get_resource_handler_service()

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
                           dir_path: AbsolutePath,
                           videoIds: list[str],
                           fileEntries: list[BaseFileEntry] | None) -> AsyncGenerator[BatchOperationStatus, None]:
        if (not videoIds and not fileEntries) or dir_path.get_path() is None:
            yield self.constructBatchOperationStatus(
                resultType=BatchResultType.Failure,
                message="No video IDs or file entries provided for batch delete"
            )

        category = dir_path.category

        try:
            if videoIds is not None:
                videos = await VideoModel.find_many(
                    {"_id": {"$in": [ObjectId(str(vid)) for vid in videoIds]}}
                ).to_list()
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
                await self._remove_videos_and_update_tags(actually_deleted, category)

            else:
                handler = self.resourceHandlerService.get_handler(category)
                paths = [handler.convert_to_DB_format_path(
                    handler.get_path_standard_format(fe.path)
                ) for fe in fileEntries]
                videos_before_delete = await VideoModel.find_many(
                    {"category": category, "path": {"$in": paths}}
                ).to_list()
                result = await VideoModel.get_pymongo_collection().delete_many(
                    {"category": category, "path": {"$in": paths}}
                )
                yield self.constructBatchOperationStatus(
                    status=f"Deleted {result.deleted_count} videos based on paths"
                )
                videos_not_deleted = await VideoModel.find_many(
                    {"category": category, "path": {"$in": paths}}
                ).to_list()
                not_deleted_paths = {v.path for v in videos_not_deleted}
                actually_deleted = [v for v in videos_before_delete if v.path not in not_deleted_paths]
                await self._remove_videos_and_update_tags(actually_deleted, category)

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

    async def batch_update(self,
                           category: str,
                           videoIDs: list[str] | None,
                           fileEntries: list[BaseFileEntry] | None,
                           author: str | None,
                           tagsOperation: TagsOperationMappingInputModel) -> AsyncGenerator[BatchOperationStatus, None]:
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
                handler = self.resourceHandlerService.get_handler(category)
                paths = [handler.convert_to_DB_format_path(
                    handler.get_path_standard_format(fe.path)
                ) for fe in fileEntries]
                video_models = await VideoModel.find_many(
                    {"category": category, "path": {"$in": paths}}
                ).to_list()
                existing_paths = {vm.path for vm in video_models}

                no_need_update_flag = await self._update_existing_videos_operations(
                    video_models,
                    findById=False,
                    author=author,
                    tagsOperation=tagsOperation,
                    update_tags=update_tags,
                    operations=operations,
                    no_need_update_flag=no_need_update_flag
                )

                new_entries = [
                    entry for entry in fileEntries
                    if handler.convert_to_DB_format_path(
                        handler.get_path_standard_format(entry.path)
                    ) not in existing_paths
                ]

                if new_entries:
                    new_operations = await asyncio.gather(*[
                        self._process_new_video_entry(
                            entry=entry,
                            category=category,
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

    async def _update_existing_videos_operations(self,
                                                 video_models: list[VideoModel],
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
                video_path = AbsolutePath.from_existing_path(video_model.path, video_model.category)
                duration = await self.thumbnailService.get_video_duration(
                    video_path.FS_format_path()
                )
                if duration is not None and duration > 0.0:
                    update_query["duration"] = duration

            if update_query:
                operations.append(UpdateOne(filter_query, {"$set": update_query}))

        if len(operations) == 0 and len(video_models) > 0:
            no_need_update_flag = True

        return no_need_update_flag

    async def _remove_videos_and_update_tags(self, actually_deleted: list[VideoModel], category: str):
        paths_to_delete = [v.path for v in actually_deleted]
        await run_in_threadpool(self._remove_videos_by_paths, paths_to_delete, category)

        update_tags: dict[str, tuple[int, bool]] = {}
        for video in actually_deleted:
            self.tagOperationService.track_tag_change(update_tags, set(video.tags or []), False)
        if update_tags:
            await self.tagOperationService.update_tag_counts(update_tags=update_tags)

    def _remove_videos_by_paths(self, paths: list[str], category: str):
        try:
            handler = self.resourceHandlerService.get_handler(category)
            for path in paths:
                handler.delete_file(handler.convert_to_FS_format_path(path))
        except Exception as e:
            logger.exception(f"Error removing video files: {e}")
            raise FileBrowseError("Error removing video files.")

    async def _process_new_video_entry(
        self,
        entry: BaseFileEntry,
        category: str,
        author: str | None,
        tagsOperation: TagsOperationMappingInputModel | None,
        update_tags: dict[str, tuple[int,bool]]
    ) -> UpdateOne:
        entry_path = AbsolutePath.from_existing_path(entry.path, category)
        handler = self.resourceHandlerService.get_handler(category)
        filter_query = {"path": entry_path.DB_format_path()}

        duration = await self.thumbnailService.get_video_duration(entry_path.FS_format_path()) or 0.0

        stat = entry.stat()
        set_on_insert = VideoModel(
            category=category,
            name=handler.get_filename_without_extension(entry.name),
            path=entry_path.DB_format_path(),
            isDir=False,
            lastModifyTime=stat.mtime,
            size=stat.size,
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
    return BatchOperationService()
