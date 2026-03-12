from functools import lru_cache
from typing import AsyncGenerator
from fastapi.concurrency import run_in_threadpool
from src.errors import InputValidationError
from src.logger import get_logger
from src.schema.types.fileBrowse_type import (
    BatchOperationStatus, 
    DirectoryVideosBatchOperationInput, 
    VideosBatchOperationInput
)
from src.services.batch_operation_service import get_batch_operation_service
from src.services.browse_file_service import get_browse_file_service
from src.services.path_convert_service import get_path_service


logger = get_logger("SubscriptionResolver")

class SubscriptionResolver:

    def __init__(self):
        self.pathHepler = get_path_service()
        self.browseFileService = get_browse_file_service()
        self.batchOperationService = get_batch_operation_service()

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
            logger.exception(f"Input validation error: {e}")
            raise InputValidationError(field="VideosBatchOperationInput", issue="Invalid input data for batch updating videos")
        
        if update:
            async for status in self.batchOperationService.batch_update(
                videoIDs=validated_input.videoIds,
                fileEntries=None,
                author=validated_input.author, 
                tagsOperation=validated_input.tagsOperation,
            ):
                yield status
        else:
            async for status in self.batchOperationService.batch_delete(
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
            logger.exception(f"Input validation error: {e}")
            raise InputValidationError(field="DirectoryVideosBatchOperationInput", issue="Invalid input data for batch updating directory videos")
        
        dir_path = self.pathHepler.get_absolute_resource_path(validated_input.relativePath)
        entries = await run_in_threadpool(self.browseFileService.get_all_video_entries_in_directory, dir_path)

        yield self.batchOperationService.constructBatchOperationStatus(
            status=f"Found {len(entries)} video entries in directory '{validated_input.relativePath.relativePath}' for batch update"
        )
        
        if update:
            async for status in self.batchOperationService.batch_update(
                None,
                entries,
                validated_input.author,
                validated_input.tagsOperation
            ):
                yield status
        else:
            async for status in self.batchOperationService.batch_delete(dir_path, None, entries):
                yield status

    

@lru_cache()
def get_subscription_resolver() -> SubscriptionResolver:
    return SubscriptionResolver()