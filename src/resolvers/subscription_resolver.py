from functools import lru_cache
from typing import AsyncGenerator
from fastapi.concurrency import run_in_threadpool
from src.errors import InputValidationError
from src.logger import get_logger
from src.schema.types.fileBrowse_type import (
    BatchOperationStatus, 
    VideosBatchOperationInput
)
from src.services.batch_operation_service import get_batch_operation_service
from src.services.browse_file_service import get_browse_file_service
from src.services.path_convert_service import AbsolutePath


logger = get_logger("SubscriptionResolver")

class SubscriptionResolver:

    def __init__(self):
        self.browseFileService = get_browse_file_service()
        self.batchOperationService = get_batch_operation_service()

    async def resolve_batch_operations(self,
                                       input: VideosBatchOperationInput,
                                       update: bool) -> AsyncGenerator[BatchOperationStatus, None]:
        """
        Resolve function to batch update or delete videos based on provided video IDs or directory path.

        :param input: Input containing video IDs or relative path for batch operation.
        :type input: VideosBatchOperationInput
        :return: An asynchronous generator yielding the status of the batch update operation.
        :rtype: AsyncGenerator[BatchOperationStatus, None]
        """
        try:
            validated_input = input.to_pydantic()
        except Exception as e:
            logger.exception(f"Input validation error: {e}")
            raise InputValidationError(field="VideosBatchOperationInput", issue="Invalid input data for batch updating videos")
        
        dir_path = AbsolutePath.from_relative_path(validated_input.relativePath.parsedPath)
        category = dir_path.category
        if validated_input.videoIds is None or len(validated_input.videoIds) == 0:
            videoIDs = None
            entries = await run_in_threadpool(
                self.browseFileService.get_all_video_entries_in_directory,
                dir_path.FS_format_path(),
                category
            )
            yield self.batchOperationService.constructBatchOperationStatus(
                status=f"Found {len(entries)} video entries in directory '{validated_input.relativePath.relativePath}' for batch update"
            )
        else:
            videoIDs = validated_input.videoIds
            entries = None

        if update:
            async for status in self.batchOperationService.batch_update(
                category=category,
                videoIDs=videoIDs,
                fileEntries=entries,
                author=validated_input.author,
                tagsOperation=validated_input.tagsOperation,
            ):
                yield status
        else:
            async for status in self.batchOperationService.batch_delete(
                dir_path=dir_path,
                videoIds=videoIDs,
                fileEntries=entries
            ):
                yield status
    

@lru_cache()
def get_subscription_resolver() -> SubscriptionResolver:
    return SubscriptionResolver()