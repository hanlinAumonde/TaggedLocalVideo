"""Tests for the migration GraphQL mutations (preflight, create, cancel)."""

import time

import pytest
from unittest.mock import AsyncMock

from src.db.models.MigrationTask_model import MigrationTaskModel, TaskStatus
from src.services.tasks.migration_service import MigrationPreflightResult
from tests.graphql.helpers import (
    MIGRATION_PREFLIGHT,
    CREATE_MIGRATION_TASK,
    CANCEL_MIGRATION_TASK,
    assert_no_errors,
    assert_error_contains,
    make_migration_path_input,
)

pytestmark = pytest.mark.mutation


# =======================================================================
# migrationPreflight
# =======================================================================

class TestMigrationPreflight:
    async def test_preflight_valid(
        self, execute_gql, mock_migration_service, video_factory,
    ):
        video = await video_factory(name="movie")

        mock_migration_service.preflight = AsyncMock(
            return_value=MigrationPreflightResult(
                valid=True,
                source_file_size=1000,
                conflict_exists=False,
                space_available=9999999,
                space_sufficient=True,
                already_migrating=False,
                same_location=False,
            )
        )

        result = await execute_gql(MIGRATION_PREFLIGHT, {
            "input": {
                "sourceVideoId": str(video.id),
                "targetDirRelativePath": make_migration_path_input("Test-category/Test-resource"),
            }
        })
        assert_no_errors(result)
        data = result.data["migrationPreflight"]
        assert data["valid"] is True
        assert data["sourceFileSize"] == "1000"
        assert data["conflictExists"] is False

    async def test_preflight_same_location(
        self, execute_gql, mock_migration_service, video_factory,
    ):
        video = await video_factory(name="a")

        mock_migration_service.preflight = AsyncMock(
            return_value=MigrationPreflightResult(
                valid=False,
                source_file_size=100,
                conflict_exists=False,
                space_available=None,
                space_sufficient=None,
                already_migrating=False,
                same_location=True,
                error_message="source path and target path are the same",
            )
        )

        result = await execute_gql(MIGRATION_PREFLIGHT, {
            "input": {
                "sourceVideoId": str(video.id),
                "targetDirRelativePath": make_migration_path_input("Test-category/Test-resource"),
            }
        })
        assert_no_errors(result)
        data = result.data["migrationPreflight"]
        assert data["valid"] is False
        assert data["sameLocation"] is True


# =======================================================================
# createMigrationTask
# =======================================================================

class TestCreateMigrationTask:
    async def test_create_task_success(
        self, execute_gql, mock_migration_service, video_factory,
    ):
        video = await video_factory(name="movie")
        now = time.time()
        mock_task = MigrationTaskModel(
            source_path="Test-category/Test-resource/movie.mp4",
            source_category="Test-category",
            target_path="Target-category/Target-resource/movie.mp4",
            target_category="Target-category",
            file_name="movie",
            file_size=1000,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        mock_migration_service.create_task = AsyncMock(return_value=mock_task)

        result = await execute_gql(CREATE_MIGRATION_TASK, {
            "input": {
                "sourceVideoId": str(video.id),
                "targetDirRelativePath": make_migration_path_input("Test-category/Test-resource"),
            }
        })
        assert_no_errors(result)
        data = result.data["createMigrationTask"]
        assert data["success"] is True
        assert data["task"]["fileName"] == "movie"
        assert data["task"]["status"] == "PENDING"

    async def test_create_task_with_conflict_strategy(
        self, execute_gql, mock_migration_service, video_factory,
    ):
        video = await video_factory(name="movie")
        now = time.time()
        mock_task = MigrationTaskModel(
            source_path="Test-category/Test-resource/movie.mp4",
            source_category="Test-category",
            target_path="Target-category/Target-resource/movie.mp4",
            target_category="Target-category",
            file_name="movie",
            file_size=1000,
            status=TaskStatus.PENDING,
            conflict_strategy="rename",
            renamed_target_path="Target-category/Target-resource/movie(1).mp4",
            created_at=now,
            updated_at=now,
        )
        mock_migration_service.create_task = AsyncMock(return_value=mock_task)

        result = await execute_gql(CREATE_MIGRATION_TASK, {
            "input": {
                "sourceVideoId": str(video.id),
                "targetDirRelativePath": make_migration_path_input("Test-category/Test-resource"),
                "conflictStrategy": "rename",
            }
        })
        assert_no_errors(result)
        data = result.data["createMigrationTask"]
        assert data["task"]["conflictStrategy"] == "rename"
        assert "movie(1)" in data["task"]["renamedTargetPath"]


# =======================================================================
# cancelMigrationTask
# =======================================================================

class TestCancelMigrationTask:
    async def test_cancel_task_success(
        self, execute_gql, mock_migration_service,
    ):
        now = time.time()
        mock_task = MigrationTaskModel(
            source_path="Test-category/Test-resource/movie.mp4",
            source_category="Test-category",
            target_path="Target-category/Target-resource/movie.mp4",
            target_category="Target-category",
            file_name="movie",
            file_size=1000,
            status=TaskStatus.CANCELLED,
            created_at=now,
            updated_at=now,
        )
        mock_migration_service.cancel_task = AsyncMock(return_value=mock_task)

        result = await execute_gql(CANCEL_MIGRATION_TASK, {
            "input": {"taskId": "507f1f77bcf86cd799439011"}
        })
        assert_no_errors(result)
        data = result.data["cancelMigrationTask"]
        assert data["success"] is True
        assert data["task"]["status"] == "CANCELLED"
