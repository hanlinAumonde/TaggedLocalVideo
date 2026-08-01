import asyncio
from dataclasses import dataclass
import time
from typing import AsyncGenerator

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.resource_handler_service import ResourceHandlerService
from src.services.tasks.state_machine import MigrationProgressStatus, StateMachine
from src.db.models.MigrationTask_model import MigrationTaskModel, TaskStatus
from src.db.models.Video_model import VideoModel
from src.errors import _MigrationCancelled, InputValidationError
from src.logger import get_logger
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.base_resource_handler import BaseResourceHandler

logger = get_logger("migration_service")

@dataclass
class MigrationPreflightResult:
    valid: bool
    source_file_size: int
    conflict_exists: bool
    space_available: int | None
    space_sufficient: bool | None
    already_migrating: bool
    same_location: bool
    error_message: str | None = None


class MigrationService(StateMachine):

    def __init__(
        self,
        resource_handler_service: ResourceHandlerService,
        dir_metadata_service: DirMetadataService,
    ):
        super().__init__(resource_handler_service, dir_metadata_service)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def preflight(
        self,
        source_path: AbsolutePath,
        target_dir_path: AbsolutePath,
    ) -> MigrationPreflightResult:
        source_handler = source_path.handler
        target_handler = target_dir_path.handler

        source_fs = source_path.FS_format_path()
        target_dir_fs = target_dir_path.FS_format_path()

        if not source_handler.file_exists(source_fs):
            return MigrationPreflightResult(
                valid=False,
                source_file_size=0,
                conflict_exists=False,
                space_available=None,
                space_sufficient=None,
                already_migrating=False,
                same_location=False,
                error_message="source file does not exist",
            )

        file_size = int(source_handler.get_size(source_fs))
        filename = source_fs.rsplit("/", 1)[-1]

        target_file_fs = target_handler.join_path(target_dir_fs, filename)

        source_db = source_path.DB_format_path()
        target_db = target_handler.convert_to_DB_format_path(target_file_fs)
        same_location = source_db == target_db

        conflict_exists = target_handler.file_exists(target_file_fs) if not same_location else False

        already_migrating = await self._is_actively_migrating(source_db)

        space_available = target_handler.get_available_space(target_dir_fs)
        if space_available is not None:
            space_sufficient = space_available >= file_size
        else:
            space_sufficient = None

        errors: list[str] = []
        if same_location:
            errors.append("source path and target path are the same")
        if already_migrating:
            errors.append("the file already has an active migration task")
        if space_sufficient is False:
            errors.append("insufficient space available at the target location")

        valid = len(errors) == 0
        error_message = ";".join(errors) if errors else None

        return MigrationPreflightResult(
            valid=valid,
            source_file_size=file_size,
            conflict_exists=conflict_exists,
            space_available=space_available,
            space_sufficient=space_sufficient,
            already_migrating=already_migrating,
            same_location=same_location,
            error_message=error_message,
        )

    async def create_task(
        self,
        source_path: AbsolutePath,
        target_dir_path: AbsolutePath,
        conflict_strategy: str | None,
    ) -> MigrationTaskModel:
        source_handler = source_path.handler
        target_handler = target_dir_path.handler

        source_fs = source_path.FS_format_path()
        target_dir_fs = target_dir_path.FS_format_path()

        if not source_handler.file_exists(source_fs):
            raise InputValidationError(field="source_path", issue="source file does not exist")

        file_size = int(source_handler.get_size(source_fs))
        filename = source_fs.rsplit("/", 1)[-1]
        file_name_no_ext = source_handler.get_filename_without_extension(filename)

        target_file_fs = target_handler.join_path(target_dir_fs, filename)
        target_db = target_handler.convert_to_DB_format_path(target_file_fs)

        renamed_target_path: str | None = None

        if target_handler.file_exists(target_file_fs):
            if conflict_strategy == "overwrite":
                pass
            elif conflict_strategy == "rename":
                target_file_fs = self._generate_unique_name(target_handler, target_dir_fs, filename)
                renamed_target_path = target_handler.convert_to_DB_format_path(target_file_fs)
            elif conflict_strategy == "skip":
                raise InputValidationError(field="conflict_strategy", issue="user chose to skip, task not created")
            else:
                raise InputValidationError(field="conflict_strategy", issue="target exists with same name but no conflict strategy specified")

        actual_target_db = renamed_target_path or target_db
        now = time.time()

        task = MigrationTaskModel(
            source_path=source_path.DB_format_path(),
            source_category=source_path.category,
            target_path=actual_target_db,
            target_category=target_dir_path.category,
            file_name=file_name_no_ext,
            file_size=file_size,
            status=TaskStatus.PENDING,
            conflict_strategy=conflict_strategy,
            renamed_target_path=renamed_target_path,
            created_at=now,
            updated_at=now,
        )

        try:
            await task.insert()
        except DuplicateKeyError:
            raise InputValidationError(
                field="source_path",
                issue="the file already has an active migration task, cannot create duplicate",
            )

        logger.info(f"Migration task created: {task.id} | {task.source_path} -> {task.target_path}")
        return task

    async def execute_migration(self, task_id: str) -> AsyncGenerator[MigrationProgressStatus, None]:
        task = await MigrationTaskModel.get(ObjectId(task_id))
        if task is None:
            raise InputValidationError(field="task_id", issue="task does not exist")
        if task.status != TaskStatus.PENDING:
            raise InputValidationError(field="task_id", issue=f"task status does not allow execution: {task.status}")

        async for status in self._run_state_machine(task, start_from=TaskStatus.PROCESSING):
            yield status

    async def cancel_task(self, task_id: str) -> MigrationTaskModel:
        task = await MigrationTaskModel.get(ObjectId(task_id))
        if task is None:
            raise InputValidationError(field="task_id", issue="task does not exist")
        if task.status not in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            raise InputValidationError(field="task_id", issue=f"current status does not allow cancellation: {task.status}")

        if task.status == TaskStatus.PENDING:
            await self._update_task_status(task, TaskStatus.CANCELLED)
        else:
            self._cancel_flags[str(task.id)] = True

        return task

    async def retry_task(self, task_id: str) -> AsyncGenerator[MigrationProgressStatus, None]:
        task = await MigrationTaskModel.get(ObjectId(task_id))
        if task is None:
            raise InputValidationError(field="task_id", issue="task does not exist")
        if task.status != TaskStatus.FAILED:
            raise InputValidationError(field="task_id", issue=f"only failed tasks can be retried, current status: {task.status}")

        start_from = TaskStatus(task.failed_step) if task.failed_step else TaskStatus.PROCESSING

        task.error_message = None
        task.failed_step = None
        task.updated_at = time.time()
        await task.save()

        async for status in self._run_state_machine(task, start_from=start_from):
            yield status

    async def is_file_locked(self, db_path: str) -> bool:
        active_statuses = [s.value for s in TaskStatus if s not in StateMachine.TERMINAL_STATUSES]
        count = await MigrationTaskModel.find(
            {
                "status": {"$in": active_statuses},
                "$or": [
                    {"source_path": db_path},
                    {"target_path": db_path},
                    {"renamed_target_path": db_path},
                ],
            }
        ).count()
        return count > 0

    # ------------------------------------------------------------------
    # Phase: PROCESSING
    # ------------------------------------------------------------------

    async def _execute_processing(
        self,
        task: MigrationTaskModel,
        source_handler: BaseResourceHandler,
        target_handler: BaseResourceHandler,
        source_fs: str,
        target_fs: str,
    ) -> AsyncGenerator[MigrationProgressStatus, None]:
        await self._update_task_status(task, TaskStatus.PROCESSING)
        yield self._make_progress(task, message="Starting copy")

        task_id = str(task.id)
        transferred = [0]

        async def progress_reader():
            async for chunk in source_handler.read_file_streaming(source_fs):
                if self._cancel_flags.get(task_id):
                    raise _MigrationCancelled()
                transferred[0] += len(chunk)
                yield chunk

        copy_task = asyncio.create_task(
            target_handler.write_file_streaming(target_fs, progress_reader())
        )

        while not copy_task.done():
            await asyncio.sleep(1)
            yield self._make_progress(task, bytes_transferred=transferred[0])

        try:
            await copy_task
        except _MigrationCancelled:
            self._cleanup_target(target_handler, target_fs)
            await self._update_task_status(task, TaskStatus.CANCELLED)
            self._cancel_flags.pop(task_id, None)
            yield self._make_progress(task, bytes_transferred=transferred[0], message="cancelled")
            return
        except Exception:
            self._cleanup_target(target_handler, target_fs)
            raise

        await self._update_task_status(task, TaskStatus.PROCESS_DONE, bytes_transferred=task.file_size)
        yield self._make_progress(task, bytes_transferred=task.file_size, message="Copy completed")

    # ------------------------------------------------------------------
    # Phase: UPDATING_DB
    # ------------------------------------------------------------------

    async def _execute_db_update(self, task: MigrationTaskModel) -> None:
        await self._update_task_status(task, TaskStatus.UPDATING_DB)

        target_path = task.renamed_target_path or task.target_path

        if task.conflict_strategy == "overwrite":
            existing = await VideoModel.find_one({"path": target_path})
            if existing:
                await existing.delete()

        video = await VideoModel.find_one({"path": task.source_path})
        if video is None:
            raise Exception(f"Source video record not found: {task.source_path}")

        video.path = target_path
        video.category = task.target_category
        await video.save()

        await self._update_task_status(task, TaskStatus.DB_UPDATED)

    # ------------------------------------------------------------------
    # Phase: DELETING_SOURCE
    # ------------------------------------------------------------------

    async def _execute_delete_source(
        self,
        task: MigrationTaskModel,
        source_handler: BaseResourceHandler,
        target_handler: BaseResourceHandler,
        source_fs: str,
    ) -> str | None:
        await self._update_task_status(task, TaskStatus.DELETING_SOURCE)

        warning = None
        try:
            source_handler.delete_file(source_fs)
        except Exception as e:
            warning = f"Source file deletion failed: {e}"
            logger.warning(f"Task {task.id}: {warning}")

        try:
            source_dir_db = source_handler.dirname(task.source_path)
            source_dir_abs = AbsolutePath.from_existing_path(
                source_dir_db, task.source_category, source_handler
            )
            await self.dirMetadataService.update_directory_metadata_forward(source_dir_abs)
        except Exception as e:
            logger.warning(f"Task {task.id}: Source directory metadata update failed: {e}")

        try:
            target_path = task.renamed_target_path or task.target_path
            target_dir_db = target_handler.dirname(target_path)
            target_dir_abs = AbsolutePath.from_existing_path(
                target_dir_db, task.target_category, target_handler
            )
            await self.dirMetadataService.update_directory_metadata_forward(target_dir_abs)
        except Exception as e:
            logger.warning(f"Task {task.id}: Target directory metadata update failed: {e}")

        await self._update_task_status(task, TaskStatus.COMPLETED)
        return warning