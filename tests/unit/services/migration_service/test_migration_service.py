"""Unit tests for MigrationService — preflight, create, cancel, execute, retry, is_file_locked."""

from pathlib import Path

import pytest

from src.db.models.MigrationTask_model import MigrationTaskModel, TaskStatus
from src.db.models.Video_model import VideoModel
from src.errors import InputValidationError
from src.services.resource_handler.absolute_path import AbsolutePath

pytestmark = pytest.mark.unit


# -----------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------

def _abs(handler_svc, category, pseudo, sub=None):
    handler = handler_svc.get_handler(category)
    return AbsolutePath.from_existing_path(
        path=handler.resolve_path(category, pseudo, sub),
        category=category,
        handler=handler,
    )


async def _collect(gen) -> list:
    result = []
    async for item in gen:
        result.append(item)
    return result


# =======================================================================
# preflight
# =======================================================================

class TestPreflight:
    async def test_valid_preflight(
        self, two_cat_migration_svc, init_db, two_cat_handler_service, local_resource_dir,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target_dir = _abs(hs, "Target-category", "Target-resource", None)

        result = await svc.preflight(source, target_dir)
        assert result.valid is True
        assert result.source_file_size == 100
        assert result.conflict_exists is False
        assert result.same_location is False
        assert result.already_migrating is False
        assert result.error_message is None

    async def test_preflight_source_not_exist(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/nonexistent.mp4")
        target_dir = _abs(hs, "Target-category", "Target-resource", None)

        result = await svc.preflight(source, target_dir)
        assert result.valid is False
        assert "source file does not exist" in result.error_message

    async def test_preflight_same_location(
        self, two_cat_migration_svc, init_db, two_cat_handler_service, local_resource_dir,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target_dir = _abs(hs, "Test-category", "Test-resource", None)

        result = await svc.preflight(source, target_dir)
        assert result.valid is False
        assert result.same_location is True
        assert "same" in result.error_message

    async def test_preflight_conflict_exists(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        local_resource_dir, target_dir,
    ):
        (target_dir / "movie_a.mp4").write_bytes(b"x" * 50)

        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target = _abs(hs, "Target-category", "Target-resource", None)

        result = await svc.preflight(source, target)
        assert result.valid is True
        assert result.conflict_exists is True

    async def test_preflight_already_migrating(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        task_factory, local_resource_dir,
    ):
        await task_factory(
            source_path="Test-category/Test-resource/movie_a.mp4",
            status=TaskStatus.PROCESSING,
        )

        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target_dir = _abs(hs, "Target-category", "Target-resource", None)

        result = await svc.preflight(source, target_dir)
        assert result.valid is False
        assert result.already_migrating is True

    async def test_preflight_space_available(
        self, two_cat_migration_svc, init_db, two_cat_handler_service, local_resource_dir,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target_dir = _abs(hs, "Target-category", "Target-resource", None)

        result = await svc.preflight(source, target_dir)
        assert result.space_available is not None
        assert result.space_available > 0
        assert result.space_sufficient is True


# =======================================================================
# create_task
# =======================================================================

class TestCreateTask:
    async def test_create_task_basic(
        self, two_cat_migration_svc, init_db, two_cat_handler_service, local_resource_dir,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target_dir = _abs(hs, "Target-category", "Target-resource", None)

        task = await svc.create_task(source, target_dir, conflict_strategy=None)
        assert task.status == TaskStatus.PENDING
        assert task.file_name == "movie_a"
        assert task.file_size == 100
        assert task.source_category == "Test-category"
        assert task.target_category == "Target-category"

    async def test_create_task_source_not_exist_raises(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/nonexistent.mp4")
        target_dir = _abs(hs, "Target-category", "Target-resource", None)

        with pytest.raises(InputValidationError, match="source file does not exist"):
            await svc.create_task(source, target_dir, conflict_strategy=None)

    async def test_create_task_conflict_overwrite(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        local_resource_dir, target_dir,
    ):
        (target_dir / "movie_a.mp4").write_bytes(b"old" * 10)

        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target = _abs(hs, "Target-category", "Target-resource", None)

        task = await svc.create_task(source, target, conflict_strategy="overwrite")
        assert task.conflict_strategy == "overwrite"
        assert task.renamed_target_path is None

    async def test_create_task_conflict_rename(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        local_resource_dir, target_dir,
    ):
        (target_dir / "movie_a.mp4").write_bytes(b"old" * 10)

        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target = _abs(hs, "Target-category", "Target-resource", None)

        task = await svc.create_task(source, target, conflict_strategy="rename")
        assert task.conflict_strategy == "rename"
        assert task.renamed_target_path is not None
        assert "(1)" in task.renamed_target_path

    async def test_create_task_conflict_skip_raises(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        local_resource_dir, target_dir,
    ):
        (target_dir / "movie_a.mp4").write_bytes(b"old" * 10)

        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target = _abs(hs, "Target-category", "Target-resource", None)

        with pytest.raises(InputValidationError, match="skip"):
            await svc.create_task(source, target, conflict_strategy="skip")

    async def test_create_task_conflict_no_strategy_raises(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        local_resource_dir, target_dir,
    ):
        (target_dir / "movie_a.mp4").write_bytes(b"old" * 10)

        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target = _abs(hs, "Target-category", "Target-resource", None)

        with pytest.raises(InputValidationError, match="no conflict strategy"):
            await svc.create_task(source, target, conflict_strategy=None)

    async def test_create_task_duplicate_raises(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        local_resource_dir,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target_dir = _abs(hs, "Target-category", "Target-resource", None)

        await svc.create_task(source, target_dir, conflict_strategy=None)
        with pytest.raises(InputValidationError, match="duplicate"):
            await svc.create_task(source, target_dir, conflict_strategy=None)


# =======================================================================
# cancel_task
# =======================================================================

class TestCancelTask:
    async def test_cancel_pending_task(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        task = await task_factory(status=TaskStatus.PENDING)

        result = await two_cat_migration_svc.cancel_task(str(task.id))
        refreshed = await MigrationTaskModel.get(task.id)
        assert refreshed.status == TaskStatus.CANCELLED

    async def test_cancel_processing_sets_flag(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        task = await task_factory(status=TaskStatus.PROCESSING)

        result = await two_cat_migration_svc.cancel_task(str(task.id))
        assert two_cat_migration_svc._cancel_flags.get(str(task.id)) is True

    async def test_cancel_nonexistent_raises(self, two_cat_migration_svc, init_db):
        from bson import ObjectId
        with pytest.raises(InputValidationError, match="does not exist"):
            await two_cat_migration_svc.cancel_task(str(ObjectId()))

    async def test_cancel_completed_raises(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        task = await task_factory(status=TaskStatus.COMPLETED)

        with pytest.raises(InputValidationError, match="does not allow cancellation"):
            await two_cat_migration_svc.cancel_task(str(task.id))


# =======================================================================
# execute_migration — full integration through all phases
# =======================================================================

class TestExecuteMigration:
    async def test_full_migration_flow(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        video_factory, local_resource_dir, target_dir,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source_handler = hs.get_handler("Test-category")
        source_fs = str(local_resource_dir / "movie_a.mp4").replace("\\", "/")
        source_db = source_handler.convert_to_DB_format_path(source_fs)
        await video_factory(name="movie_a", path=source_db)

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target = _abs(hs, "Target-category", "Target-resource", None)

        task = await svc.create_task(source, target, conflict_strategy=None)
        events = await _collect(svc.execute_migration(str(task.id)))

        assert len(events) >= 3

        refreshed = await MigrationTaskModel.get(task.id)
        assert refreshed.status == TaskStatus.COMPLETED

        assert not (local_resource_dir / "movie_a.mp4").exists()
        assert (target_dir / "movie_a.mp4").exists()
        assert (target_dir / "movie_a.mp4").read_bytes() == b"a" * 100

        target_handler = hs.get_handler("Target-category")
        target_fs = str(target_dir / "movie_a.mp4").replace("\\", "/")
        target_db = target_handler.convert_to_DB_format_path(target_fs)
        video = await VideoModel.find_one({"path": target_db})
        assert video is not None
        assert video.category == "Target-category"

    async def test_execute_nonexistent_task_raises(
        self, two_cat_migration_svc, init_db,
    ):
        from bson import ObjectId
        with pytest.raises(InputValidationError, match="does not exist"):
            await _collect(two_cat_migration_svc.execute_migration(str(ObjectId())))

    async def test_execute_non_pending_task_raises(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        task = await task_factory(status=TaskStatus.COMPLETED)
        with pytest.raises(InputValidationError, match="does not allow execution"):
            await _collect(two_cat_migration_svc.execute_migration(str(task.id)))

    async def test_migration_with_overwrite(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        video_factory, local_resource_dir, target_dir,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source_handler = hs.get_handler("Test-category")
        source_fs = str(local_resource_dir / "movie_b.mp4").replace("\\", "/")
        source_db = source_handler.convert_to_DB_format_path(source_fs)
        await video_factory(name="movie_b", path=source_db)

        (target_dir / "movie_b.mp4").write_bytes(b"old" * 50)
        target_handler = hs.get_handler("Target-category")
        target_fs = str(target_dir / "movie_b.mp4").replace("\\", "/")
        target_db = target_handler.convert_to_DB_format_path(target_fs)
        await video_factory(
            name="movie_b_old", path=target_db, category="Target-category",
        )

        source = _abs(hs, "Test-category", "Test-resource", "/movie_b.mp4")
        target = _abs(hs, "Target-category", "Target-resource", None)

        task = await svc.create_task(source, target, conflict_strategy="overwrite")
        await _collect(svc.execute_migration(str(task.id)))

        refreshed = await MigrationTaskModel.get(task.id)
        assert refreshed.status == TaskStatus.COMPLETED

        assert (target_dir / "movie_b.mp4").read_bytes() == b"b" * 200

        videos = await VideoModel.find({"path": target_db}).to_list()
        assert len(videos) == 1
        assert videos[0].category == "Target-category"

    async def test_migration_with_rename(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        video_factory, local_resource_dir, target_dir,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source_handler = hs.get_handler("Test-category")
        source_fs = str(local_resource_dir / "movie_a.mp4").replace("\\", "/")
        source_db = source_handler.convert_to_DB_format_path(source_fs)
        await video_factory(name="movie_a", path=source_db)

        (target_dir / "movie_a.mp4").write_bytes(b"existing")

        source = _abs(hs, "Test-category", "Test-resource", "/movie_a.mp4")
        target = _abs(hs, "Target-category", "Target-resource", None)

        task = await svc.create_task(source, target, conflict_strategy="rename")
        await _collect(svc.execute_migration(str(task.id)))

        assert (target_dir / "movie_a(1).mp4").exists()
        assert (target_dir / "movie_a(1).mp4").read_bytes() == b"a" * 100
        assert (target_dir / "movie_a.mp4").read_bytes() == b"existing"


# =======================================================================
# retry_task
# =======================================================================

class TestRetryTask:
    async def test_retry_failed_task(
        self, two_cat_migration_svc, init_db, two_cat_handler_service,
        video_factory, local_resource_dir, target_dir, task_factory,
    ):
        svc = two_cat_migration_svc
        hs = two_cat_handler_service

        source_handler = hs.get_handler("Test-category")
        source_fs = str(local_resource_dir / "movie_a.mp4").replace("\\", "/")
        source_db = source_handler.convert_to_DB_format_path(source_fs)
        await video_factory(name="movie_a", path=source_db)

        target_handler = hs.get_handler("Target-category")
        target_fs = str(target_dir / "movie_a.mp4").replace("\\", "/")
        target_db = target_handler.convert_to_DB_format_path(target_fs)

        task = await task_factory(
            source_path=source_db,
            target_path=target_db,
            target_category="Target-category",
            status=TaskStatus.FAILED,
            file_size=100,
            failed_step=TaskStatus.PROCESSING,
            error_message="previous failure",
        )

        events = await _collect(svc.retry_task(str(task.id)))
        assert len(events) >= 1

        refreshed = await MigrationTaskModel.get(task.id)
        assert refreshed.status == TaskStatus.COMPLETED

    async def test_retry_nonexistent_raises(self, two_cat_migration_svc, init_db):
        from bson import ObjectId
        with pytest.raises(InputValidationError, match="does not exist"):
            await _collect(two_cat_migration_svc.retry_task(str(ObjectId())))

    async def test_retry_non_failed_raises(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        task = await task_factory(status=TaskStatus.PENDING)
        with pytest.raises(InputValidationError, match="only failed tasks"):
            await _collect(two_cat_migration_svc.retry_task(str(task.id)))


# =======================================================================
# is_file_locked
# =======================================================================

class TestIsFileLocked:
    async def test_no_tasks_not_locked(self, two_cat_migration_svc, init_db):
        assert await two_cat_migration_svc.is_file_locked("some/path") is False

    async def test_pending_task_locks_source(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        await task_factory(
            source_path="Test-category/Test-resource/locked.mp4",
            status=TaskStatus.PENDING,
        )
        assert await two_cat_migration_svc.is_file_locked(
            "Test-category/Test-resource/locked.mp4"
        ) is True

    async def test_completed_task_does_not_lock(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        await task_factory(
            source_path="Test-category/Test-resource/done.mp4",
            status=TaskStatus.COMPLETED,
        )
        assert await two_cat_migration_svc.is_file_locked(
            "Test-category/Test-resource/done.mp4"
        ) is False

    async def test_locks_target_path(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        await task_factory(
            target_path="Target-category/Target-resource/target.mp4",
            status=TaskStatus.PROCESSING,
        )
        assert await two_cat_migration_svc.is_file_locked(
            "Target-category/Target-resource/target.mp4"
        ) is True

    async def test_locks_renamed_target_path(
        self, two_cat_migration_svc, init_db, task_factory,
    ):
        await task_factory(
            renamed_target_path="Target-category/Target-resource/movie_a(1).mp4",
            status=TaskStatus.PROCESSING,
        )
        assert await two_cat_migration_svc.is_file_locked(
            "Target-category/Target-resource/movie_a(1).mp4"
        ) is True
