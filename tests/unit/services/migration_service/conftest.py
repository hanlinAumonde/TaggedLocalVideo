import time
from pathlib import Path
from typing import Callable

import pytest
import pytest_asyncio

from src.config import Settings
from src.db.models.MigrationTask_model import MigrationTaskModel, TaskStatus
from src.services.cache.cache_service import CacheService
from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.resource_handler_service import ResourceHandlerService
from src.services.tasks.migration_service import MigrationService


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


@pytest_asyncio.fixture
def task_factory(init_db) -> Callable:
    """Factory fixture to create MigrationTaskModel documents in the test DB."""
    async def _create(**kwargs) -> MigrationTaskModel:
        now = time.time()
        defaults = {
            "source_path": "Test-category/Test-resource/movie_a.mp4",
            "source_category": "Test-category",
            "target_path": "Target-category/Target-resource/movie_a.mp4",
            "target_category": "Target-category",
            "file_name": "movie_a",
            "file_size": 100,
            "status": TaskStatus.PENDING,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(kwargs)
        task = MigrationTaskModel(**defaults)
        await task.insert()
        return task
    return _create
