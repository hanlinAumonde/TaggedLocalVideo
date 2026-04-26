from enum import Enum
import strawberry
from typing_extensions import Annotated
from fastapi import Depends
from src.config import Settings, get_settings

from src.config import Settings
from src.services.batch_operation_service import BatchOperationService
from src.services.browse_file_service import BrowseFileService
from src.services.cache.cache_service import CacheService
from src.services.dir_metadata_service import DirMetadataService
from src.services.ffmpeg_service import FFmpegService
from src.services.resource_handler.resource_handler_service import ResourceHandlerService
from src.services.series_service import SeriesService
from src.services.tag_operation_service import TagOperationService
from src.services.thumbnail_service import ThumbnailService
from src.services.video_stream_service import VideoStreamService

class ContextEnum(Enum):
    SETTINGS = Settings
    CACHE_SERVICE = CacheService
    RESOURCE_HANDLER_SERVICE = ResourceHandlerService
    FFMPEG_SERVICE = FFmpegService
    THUMBNAIL_SERVICE = ThumbnailService
    TAG_OPERATION_SERVICE = TagOperationService
    SERIES_SERVICE = SeriesService
    DIR_METADATA_SERVICE = DirMetadataService
    BROWSE_FILE_SERVICE = BrowseFileService
    BATCH_OPERATION_SERVICE = BatchOperationService

def get_cache_service(settings:Settings = Depends(get_settings)):
    return CacheService(config=settings.cache_config)
# CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]

def get_resource_handler_service(settings:Settings = Depends(get_settings)):
    return ResourceHandlerService(settings=settings)
ResourceHandlerServiceDep = Annotated[ResourceHandlerService, Depends(get_resource_handler_service)]

def get_ffmpeg_service(settings:Settings = Depends(get_settings)):
    return FFmpegService(semaphore_limit=settings.ffmpeg_semaphore_limit)
FFmpegServiceDep = Annotated[FFmpegService, Depends(get_ffmpeg_service)]

def get_tag_operation_service(settings:Settings = Depends(get_settings)):
    return TagOperationService(settings=settings)
# TagOperationServiceDep = Annotated[TagOperationService, Depends(get_tag_operation_service)]

def get_series_service():
    return SeriesService()
# SeriesServiceDep = Annotated[SeriesService, Depends(get_series_service)]

def get_dir_metadata_service(
    settings: Settings = Depends(get_settings),
    resource_handler_service = Depends(get_resource_handler_service), 
    cache_service = Depends(get_cache_service)
):
    return DirMetadataService(
        settings=settings, 
        resource_handler_service=resource_handler_service, 
        cache_service=cache_service
    )
# DirMetadataServiceDep = Annotated[DirMetadataService, Depends(get_dir_metadata_service)]

def get_thumbnail_service(
    resource_handler_service = Depends(get_resource_handler_service), 
    ffmpeg = Depends(get_ffmpeg_service),
    settings: Settings = Depends(get_settings)
):
    return ThumbnailService(
        settings=settings,
        resource_handler_service=resource_handler_service, 
        ffmpeg_service=ffmpeg
    )
ThumbnailServiceDep = Annotated[ThumbnailService, Depends(get_thumbnail_service)]

def get_browse_file_service(
    settings: Settings = Depends(get_settings),
    dir_metadata_service = Depends(get_dir_metadata_service), 
    resource_handler_service = Depends(get_resource_handler_service)
):
    return BrowseFileService(
        settings=settings, 
        dir_metadata_service=dir_metadata_service, 
        resource_handler_service=resource_handler_service
    )
# BrowseFileServiceDep = Annotated[BrowseFileService, Depends(get_browse_file_service)]

def get_batch_operation_service(
    dir_metadata_service = Depends(get_dir_metadata_service),
    tag_operation_service = Depends(get_tag_operation_service),
    thumbnail_service = Depends(get_thumbnail_service),
    resource_handler_service = Depends(get_resource_handler_service),
    ffmpeg_service = Depends(get_ffmpeg_service),
):
    return BatchOperationService(
        dir_metadata_service=dir_metadata_service,
        tag_operation_service=tag_operation_service,
        thumbnail_service=thumbnail_service,
        resource_handler_service=resource_handler_service,
        ffmpeg_service=ffmpeg_service,
    )
# BatchOperationServiceDep = Annotated[BatchOperationService, Depends(get_batch_operation_service)]

def get_video_stream_service(
    resource_handler_service = Depends(get_resource_handler_service),
    ffmpeg_service = Depends(get_ffmpeg_service)
):
    return VideoStreamService(
        resourceHandlerService=resource_handler_service, 
        ffmpegService=ffmpeg_service
    )
VideoStreamServiceDep = Annotated[VideoStreamService, Depends(get_video_stream_service)]

async def get_context(
    settings: Settings = Depends(get_settings),
    cache_service: CacheService = Depends(get_cache_service),
    resource_handler_service: ResourceHandlerService = Depends(get_resource_handler_service),
    ffmpeg_service: FFmpegService = Depends(get_ffmpeg_service),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
    tag_operation_service: TagOperationService = Depends(get_tag_operation_service),
    series_service: SeriesService = Depends(get_series_service),
    dir_metadata_service: DirMetadataService = Depends(get_dir_metadata_service),
    browse_file_service: BrowseFileService = Depends(get_browse_file_service),
    batch_operation_service: BatchOperationService = Depends(get_batch_operation_service),
):
    return {
        ContextEnum.SETTINGS: settings,
        ContextEnum.CACHE_SERVICE: cache_service,
        ContextEnum.RESOURCE_HANDLER_SERVICE: resource_handler_service,
        ContextEnum.FFMPEG_SERVICE: ffmpeg_service,
        ContextEnum.THUMBNAIL_SERVICE: thumbnail_service,
        ContextEnum.TAG_OPERATION_SERVICE: tag_operation_service,
        ContextEnum.SERIES_SERVICE: series_service,
        ContextEnum.DIR_METADATA_SERVICE: dir_metadata_service,
        ContextEnum.BROWSE_FILE_SERVICE: browse_file_service,
        ContextEnum.BATCH_OPERATION_SERVICE: batch_operation_service,
    }

def get_context_value(info: strawberry.Info, key: ContextEnum):
    return info.context[key]