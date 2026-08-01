import time

import strawberry
from bson import ObjectId
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from src.context import ContextEnum, get_context_value
from src.db.models.Video_model import VideoModel
from src.errors import DatabaseOperationError, InputValidationError, VideoNotFoundError
from src.services.tasks.migration_service import MigrationService
from src.logger import get_logger
from src.schema.types.fileBrowse_type import VideoMutationResult
from src.schema.types.pydantic_types.batch_operation_type import SeriesOrderEntryInputModel
from src.schema.types.video_type import UpdateVideoMetadataInput, Video
from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.resource_handler_service import ResourceHandlerService
from src.services.tag_operation_service import TagOperationService

logger = get_logger("mutation_resolver")

#class MutationResolver:

async def resolve_update_video_metadata(input: UpdateVideoMetadataInput, info: strawberry.Info) -> VideoMutationResult:
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
            migration_service: MigrationService = get_context_value(info, ContextEnum.MIGRATION_SERVICE)
            if await migration_service.is_file_locked(video_model.path):
                raise InputValidationError(field="videoId", issue="the file is being migrated and cannot be modified")

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

            # series field: None = no change; clear=True = wipe this video only;
            # otherwise (name + orders) = rewrite the whole series ordering
            series_bulk_ops: list[UpdateOne] = []
            if validated_input.series is not None:
                if validated_input.series.clear:
                    video_model.seriesName = None
                    video_model.seriesOrder = None
                else:
                    series_bulk_ops = await _build_series_rewrite_ops(
                        current_video_id=str(video_model.id),
                        target_series_name=validated_input.series.name,
                        orders=validated_input.series.orders,
                    )
                    # Reflect the new membership/order on the in-memory model
                    # so the returned Video reflects the change without a reload.
                    for entry in validated_input.series.orders:
                        if entry.videoId == str(video_model.id):
                            video_model.seriesName = validated_input.series.name
                            video_model.seriesOrder = entry.order
                            break

            await video_model.save()
            if series_bulk_ops:
                try:
                    await VideoModel.get_pymongo_collection().bulk_write(series_bulk_ops)
                except BulkWriteError as bwe:
                    logger.exception(f"Bulk write error during series rewrite: {bwe.details}")
                    raise DatabaseOperationError("update_video_metadata", "series_bulk_write_failure")
            tagOperationService: TagOperationService = get_context_value(info, ContextEnum.TAG_OPERATION_SERVICE)
            await tagOperationService.update_tag_counts(update_tags=update_tags)

            updated_video = await Video.from_mongoDB(video_model)
            return VideoMutationResult(success=True, video=updated_video)

    except VideoNotFoundError:
        logger.exception(f"Video not found: {validated_input.videoId}")
        raise
    except InputValidationError:
        raise
    except Exception as e:
        logger.exception(f"Database operation error during update video metadata: {e}")
        raise DatabaseOperationError("update_video_metadata", f"videoId-{validated_input.videoId}")

async def _build_series_rewrite_ops(
    current_video_id: str,
    target_series_name: str,
    orders: list[SeriesOrderEntryInputModel],
) -> list[UpdateOne]:
    """
    Build bulk UpdateOne ops that rewrite a whole series ordering.

    Strict validation:
    - `orders` must be non-empty and contain `current_video_id`.
    - Every videoId in `orders` (other than `current_video_id`) must currently
        already belong to `target_series_name`; this prevents one edit-panel save
        from dragging videos out of another series.
    - Order values within `orders` must be unique.
    """
    if not orders:
        raise InputValidationError(
            field="series.orders",
            issue="orders must be non-empty when assigning a series",
        )

    id_to_order: dict[str, int] = {}
    seen_orders: set[int] = set()
    for entry in orders:
        if entry.videoId in id_to_order:
            raise InputValidationError(
                field="series.orders",
                issue=f"duplicate videoId in orders: {entry.videoId}",
            )
        if entry.order in seen_orders:
            raise InputValidationError(
                field="series.orders",
                issue=f"duplicate order value in orders: {entry.order}",
            )
        id_to_order[entry.videoId] = entry.order
        seen_orders.add(entry.order)

    if current_video_id not in id_to_order:
        raise InputValidationError(
            field="series.orders",
            issue="orders must include the current video being edited",
        )

    other_ids = [vid for vid in id_to_order.keys() if vid != current_video_id]
    if other_ids:
        try:
            other_object_ids = [ObjectId(vid) for vid in other_ids]
        except Exception:
            raise InputValidationError(
                field="series.orders",
                issue="invalid videoId in orders",
            )
        cursor = VideoModel.find(
            {"_id": {"$in": other_object_ids}}
        )
        existing_models = await cursor.to_list()
        existing_by_id = {str(m.id): m for m in existing_models}
        missing = [vid for vid in other_ids if vid not in existing_by_id]
        if missing:
            raise InputValidationError(
                field="series.orders",
                issue=f"videoIds not found: {missing}",
            )
        foreign = [
            vid for vid, m in existing_by_id.items()
            if m.seriesName != target_series_name
        ]
        if foreign:
            raise InputValidationError(
                field="series.orders",
                issue=(
                    f"videoIds do not currently belong to series "
                    f"'{target_series_name}': {foreign}"
                ),
            )

    ops: list[UpdateOne] = []
    for vid, order in id_to_order.items():
        if vid == current_video_id:
            # current video is saved via video_model.save() above
            continue
        ops.append(
            UpdateOne(
                {"_id": ObjectId(vid)},
                {"$set": {"seriesName": target_series_name, "seriesOrder": order}},
            )
        )
    return ops

async def resolve_record_video_view(videoId: strawberry.ID) -> VideoMutationResult:
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

async def resolve_delete_video(videoId: strawberry.ID, info: strawberry.Info) -> VideoMutationResult:
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

        migration_service: MigrationService = get_context_value(info, ContextEnum.MIGRATION_SERVICE)
        if await migration_service.is_file_locked(video_model.path):
            raise InputValidationError(field="videoId", issue="the file is being migrated and cannot be deleted")

        old_tags = set(video_model.tags or [])
        resourceHandlerService: ResourceHandlerService = get_context_value(info, ContextEnum.RESOURCE_HANDLER_SERVICE)
        handler = resourceHandlerService.get_handler(video_model.category)
        video_path = AbsolutePath.from_existing_path(
            path=video_model.path, 
            category=video_model.category,
            handler=handler
        )

        await video_model.delete()
        tagOperationService: TagOperationService = get_context_value(info, ContextEnum.TAG_OPERATION_SERVICE)
        await tagOperationService.update_tag_counts(update_tags={tag: (1, False) for tag in old_tags})

        video_FS_path = video_path.FS_format_path()
        handler.delete_file(video_FS_path)

        directory_path = handler.dirname(video_FS_path)
        if directory_path:
            dirMetadataService: DirMetadataService = get_context_value(info, ContextEnum.DIR_METADATA_SERVICE)
            await dirMetadataService.update_directory_metadata_forward(
                AbsolutePath.from_existing_path(
                    path=directory_path, 
                    category=video_model.category, 
                    handler=handler
                )
            )
            
        return VideoMutationResult(success=True, video=None)

    except VideoNotFoundError:
        logger.exception(f"Video not found: {videoId}")
        raise
    except Exception as e:
        logger.exception(f"Database operation error during delete video: {e}")
        raise DatabaseOperationError("delete_video", f"videoId-{videoId}")