import pytest

from src.config import Settings
from src.services.cache.cache_service import CacheService
from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.resource_handler_service import ResourceHandlerService


@pytest.fixture
def dir_svc(
    fs_settings: Settings,
    local_resource_handler_service: ResourceHandlerService,
    local_cache_service: CacheService,
) -> DirMetadataService:
    return DirMetadataService(
        settings=fs_settings,
        resource_handler_service=local_resource_handler_service,
        cache_service=local_cache_service,
    )


# def _abs_path(path: str, handler_svc: ResourceHandlerService) -> AbsolutePath:
#     handler = handler_svc.get_handler("Test-category")
#     return AbsolutePath.from_existing_path(
#         path=path, category="Test-category", handler=handler,
#     )
