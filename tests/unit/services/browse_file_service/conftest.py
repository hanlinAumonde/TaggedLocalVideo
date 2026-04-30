
import pytest

from src.config import Settings
from src.services.browse_file_service import BrowseFileService
from src.services.cache.cache_service import CacheService
from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.resource_handler_service import ResourceHandlerService


@pytest.fixture
def dir_meta_svc(
    fs_settings: Settings,
    local_resource_handler_service: ResourceHandlerService,
    local_cache_service: CacheService,
) -> DirMetadataService:
    return DirMetadataService(
        settings=fs_settings,
        resource_handler_service=local_resource_handler_service,
        cache_service=local_cache_service,
    )


@pytest.fixture
def browse_svc(
    fs_settings: Settings,
    dir_meta_svc: DirMetadataService,
    local_resource_handler_service: ResourceHandlerService,
) -> BrowseFileService:
    return BrowseFileService(
        settings=fs_settings,
        dir_metadata_service=dir_meta_svc,
        resource_handler_service=local_resource_handler_service,
    )
