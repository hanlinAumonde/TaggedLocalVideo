from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import Settings
from src.services.batch_operation_service import BatchOperationService
from src.services.cache.cache_service import CacheService
from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.resource_handler_service import ResourceHandlerService
from src.services.tag_operation_service import TagOperationService


@pytest.fixture
def mock_ffmpeg():
    svc = MagicMock(name="FFmpegService")
    svc.get_video_duration = AsyncMock(return_value=120.0)
    return svc


@pytest.fixture
def mock_thumbnail():
    return MagicMock(name="ThumbnailService")


@pytest.fixture
def batch_svc(
    fs_settings: Settings,
    local_resource_handler_service: ResourceHandlerService,
    local_cache_service: CacheService,
    mock_ffmpeg,
    mock_thumbnail,
) -> BatchOperationService:
    dir_meta = DirMetadataService(
        settings=fs_settings,
        resource_handler_service=local_resource_handler_service,
        cache_service=local_cache_service,
    )
    tag_ops = TagOperationService(settings=fs_settings)
    return BatchOperationService(
        dir_metadata_service=dir_meta,
        tag_operation_service=tag_ops,
        thumbnail_service=mock_thumbnail,
        resource_handler_service=local_resource_handler_service,
        ffmpeg_service=mock_ffmpeg,
    )
