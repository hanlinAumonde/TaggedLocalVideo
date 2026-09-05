from pathlib import Path

import pytest

from src.config import Settings
from src.platform.cache.cache_service import CacheService
from src.features.browsing.dir_metadata_service import DirMetadataService
from src.platform.storage.resource_handler_service import ResourceHandlerService
from src.features.migration.migration_service import MigrationService


@pytest.fixture
def migration_svc(
    fs_settings: Settings,
    local_resource_handler_service: ResourceHandlerService,
    local_cache_service: CacheService,
) -> MigrationService:
    dir_meta = DirMetadataService(
        settings=fs_settings,
        resource_handler_service=local_resource_handler_service,
        cache_service=local_cache_service,
    )
    return MigrationService(
        resource_handler_service=local_resource_handler_service,
        dir_metadata_service=dir_meta,
    )


@pytest.fixture
def target_dir(tmp_path: Path) -> Path:
    """A separate target directory for migration tests."""
    d = tmp_path / "target"
    d.mkdir()
    return d


@pytest.fixture
def two_category_settings(
    test_settings: Settings,
    local_resource_dir: Path,
    target_dir: Path,
    monkeypatch,
) -> Settings:
    """Settings with two categories: source and target, pointing at real dirs."""
    from src import config
    payload = test_settings.model_dump()
    payload["resource_paths"] = {
        "Test-category": {"Test-resource": str(local_resource_dir)},
        "Target-category": {"Target-resource": str(target_dir)},
    }
    settings = Settings.model_validate(payload)
    monkeypatch.setattr(config, "_settings", settings)
    return settings


@pytest.fixture
def two_cat_handler_service(two_category_settings: Settings) -> ResourceHandlerService:
    return ResourceHandlerService(settings=two_category_settings)


@pytest.fixture
def two_cat_cache_service(two_category_settings: Settings) -> CacheService:
    return CacheService(config=two_category_settings.cache_config)


@pytest.fixture
def two_cat_migration_svc(
    two_category_settings: Settings,
    two_cat_handler_service: ResourceHandlerService,
    two_cat_cache_service: CacheService,
) -> MigrationService:
    dir_meta = DirMetadataService(
        settings=two_category_settings,
        resource_handler_service=two_cat_handler_service,
        cache_service=two_cat_cache_service,
    )
    return MigrationService(
        resource_handler_service=two_cat_handler_service,
        dir_metadata_service=dir_meta,
    )
