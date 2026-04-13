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
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.resource_handler_service import get_resource_handler_service


logger = get_logger("SubscriptionResolver")

class SubscriptionResolver:

    def __init__(self):
        self.browseFileService = get_browse_file_service()
        self.batchOperationService = get_batch_operation_service()
        self.resourceHandlerService = get_resource_handler_service()

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

        series_operation = validated_input.seriesOperation
        by_ids = validated_input.videoIds is not None and len(validated_input.videoIds) > 0

        if series_operation is not None:
            if not update:
                raise InputValidationError(field="seriesOperation", issue="Series operation is only allowed in batch update, not delete")
            if not by_ids:
                raise InputValidationError(field="seriesOperation", issue="Series operation requires an explicit videoIds list")
            if not series_operation.clear:
                if not series_operation.name:
                    raise InputValidationError(field="seriesOperation", issue="Series name is required when clear is false")
                orders_ids = {entry.videoId for entry in series_operation.orders}
                selected_ids = set(validated_input.videoIds)
                if orders_ids != selected_ids:
                    raise InputValidationError(field="seriesOperation", issue="Series orders must cover exactly the selected video IDs")

        if by_ids:
            # By video IDs — single batch call, no path expansion needed
            if update:
                async for status in self.batchOperationService.batch_update(
                    category=category,
                    videoIDs=validated_input.videoIds,
                    fileEntries=None,
                    author=validated_input.author,
                    tagsOperation=validated_input.tagsOperation,
                    seriesOperation=series_operation,
                ):
                    yield status
            else:
                async for status in self.batchOperationService.batch_delete(
                    dir_path=dir_path,
                    videoIds=validated_input.videoIds,
                    fileEntries=None
                ):
                    yield status
            return

        # By directory path — expand virtual paths to real mounted paths, collect all entries
        category_path_pairs = self._expand_directory_path(dir_path)
        all_entries = []
        for cat, abs_path in category_path_pairs:
            entries = await run_in_threadpool(
                self.browseFileService.get_all_video_entries_in_directory,
                abs_path.FS_format_path(),
                cat
            )
            if entries:
                all_entries.extend(entries)
                yield self.batchOperationService.constructBatchOperationStatus(
                    status=f"Scanning '{abs_path.get_path()}' — {len(all_entries)} videos found so far"
                )

        yield self.batchOperationService.constructBatchOperationStatus(
            status=f"Found {len(all_entries)} video entries in '{validated_input.relativePath.relativePath}'"
        )

        if update:
            async for status in self.batchOperationService.batch_update(
                category=category,
                videoIDs=None,
                fileEntries=all_entries,
                author=validated_input.author,
                tagsOperation=validated_input.tagsOperation,
            ):
                yield status
        else:
            async for status in self.batchOperationService.batch_delete(
                dir_path=dir_path,
                videoIds=None,
                fileEntries=all_entries
            ):
                yield status

    def _expand_directory_path(self, dir_path: AbsolutePath) -> list[tuple[str, AbsolutePath]]:
        """
        Expand a virtual directory path (root/category level) into real mounted paths.

        :param dir_path: The virtual directory path to expand
        :type dir_path: AbsolutePath
        :return: A list of tuples containing the category and the corresponding absolute path
        :rtype: list[tuple[str, AbsolutePath]]
        """
        if dir_path.is_root_level():
            return [
                (cat, AbsolutePath.from_relative_path((cat, pn, None)))
                for cat in self.resourceHandlerService.get_all_categories()
                for pn in self.resourceHandlerService.get_pseudo_names(cat)
            ]
        elif dir_path.is_category_level():
            category = dir_path.category
            return [
                (category, AbsolutePath.from_relative_path((category, pn, None)))
                for pn in self.resourceHandlerService.get_pseudo_names(category)
            ]
        else:
            return [(dir_path.category, dir_path)]
    

@lru_cache()
def get_subscription_resolver() -> SubscriptionResolver:
    return SubscriptionResolver()