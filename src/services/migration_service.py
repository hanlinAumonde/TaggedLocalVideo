import asyncio
import time
from dataclasses import dataclass
from typing import AsyncGenerator

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from src.db.models.MigrationTask_model import MigrationTaskModel, MigrationStatus
from src.db.models.Video_model import VideoModel
from src.errors import InputValidationError
from src.logger import get_logger
from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.base_resource_handler import BaseResourceHandler
from src.services.resource_handler.resource_handler_service import ResourceHandlerService

logger = get_logger("migration_service")

TERMINAL_STATUSES = {MigrationStatus.COMPLETED, MigrationStatus.FAILED, MigrationStatus.CANCELLED}

_PHASE_ORDER = [MigrationStatus.COPYING, MigrationStatus.UPDATING_DB, MigrationStatus.DELETING_SOURCE]


class _MigrationCancelled(Exception):
    pass


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


@dataclass
class MigrationProgressStatus:
    task_id: str
    status: str
    bytes_transferred: int
    total_bytes: int
    progress_percentage: float
    message: str | None = None


class MigrationService:

    def __init__(
        self,
        resource_handler_service: ResourceHandlerService,
        dir_metadata_service: DirMetadataService,
    ):
        self.resourceHandlerService = resource_handler_service
        self.dirMetadataService = dir_metadata_service
        self._cancel_flags: dict[str, bool] = {}

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
        error_message = "；".join(errors) if errors else None

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
            status=MigrationStatus.PENDING,
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
        if task.status != MigrationStatus.PENDING:
            raise InputValidationError(field="task_id", issue=f"task status does not allow execution: {task.status}")

        async for status in self._run_state_machine(task, start_from=MigrationStatus.COPYING):
            yield status

    async def cancel_task(self, task_id: str) -> MigrationTaskModel:
        task = await MigrationTaskModel.get(ObjectId(task_id))
        if task is None:
            raise InputValidationError(field="task_id", issue="task does not exist")
        if task.status not in (MigrationStatus.PENDING, MigrationStatus.COPYING):
            raise InputValidationError(field="task_id", issue=f"current status does not allow cancellation: {task.status}")

        if task.status == MigrationStatus.PENDING:
            await self._update_task_status(task, MigrationStatus.CANCELLED)
        else:
            self._cancel_flags[str(task.id)] = True

        return task

    async def retry_task(self, task_id: str) -> AsyncGenerator[MigrationProgressStatus, None]:
        task = await MigrationTaskModel.get(ObjectId(task_id))
        if task is None:
            raise InputValidationError(field="task_id", issue="task does not exist")
        if task.status != MigrationStatus.FAILED:
            raise InputValidationError(field="task_id", issue=f"only failed tasks can be retried, current status: {task.status}")

        start_from = MigrationStatus(task.failed_step) if task.failed_step else MigrationStatus.COPYING

        task.error_message = None
        task.failed_step = None
        task.updated_at = time.time()
        await task.save()

        async for status in self._run_state_machine(task, start_from=start_from):
            yield status

    async def is_file_locked(self, db_path: str) -> bool:
        active_statuses = [s.value for s in MigrationStatus if s not in TERMINAL_STATUSES]
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
    # State machine
    # ------------------------------------------------------------------

    async def _run_state_machine(
        self,
        task: MigrationTaskModel,
        start_from: MigrationStatus,
    ) -> AsyncGenerator[MigrationProgressStatus, None]:
        source_handler = self.resourceHandlerService.get_handler(task.source_category)
        target_handler = self.resourceHandlerService.get_handler(task.target_category)

        source_fs = source_handler.convert_to_FS_format_path(task.source_path)
        target_db = task.renamed_target_path or task.target_path
        target_fs = target_handler.convert_to_FS_format_path(target_db)

        try:
            if self._should_run_phase(start_from, MigrationStatus.COPYING):
                async for progress in self._execute_copy(
                    task, source_handler, target_handler, source_fs, target_fs
                ):
                    yield progress
                if task.status == MigrationStatus.CANCELLED:
                    return

            if self._should_run_phase(start_from, MigrationStatus.UPDATING_DB):
                await self._execute_db_update(task)
                yield self._make_progress(task, message="Database updated")

            if self._should_run_phase(start_from, MigrationStatus.DELETING_SOURCE):
                warning = await self._execute_delete_source(
                    task, source_handler, target_handler, source_fs
                )
                yield self._make_progress(task, message=warning or "Migration completed")

        except Exception as e:
            logger.exception(f"Migration task {task.id} failed: {e}")
            failed_step = task.status if task.status not in TERMINAL_STATUSES else MigrationStatus.COPYING
            await self._update_task_status(
                task,
                MigrationStatus.FAILED,
                error_message=str(e),
                failed_step=str(failed_step),
            )
            yield self._make_progress(task, message=f"Migration failed: {e}")

    @staticmethod
    def _should_run_phase(start_from: MigrationStatus, phase: MigrationStatus) -> bool:
        order = {s: i for i, s in enumerate(_PHASE_ORDER)}
        return order.get(phase, 0) >= order.get(start_from, 0)

    # ------------------------------------------------------------------
    # Phase: COPYING
    # ------------------------------------------------------------------

    async def _execute_copy(
        self,
        task: MigrationTaskModel,
        source_handler: BaseResourceHandler,
        target_handler: BaseResourceHandler,
        source_fs: str,
        target_fs: str,
    ) -> AsyncGenerator[MigrationProgressStatus, None]:
        await self._update_task_status(task, MigrationStatus.COPYING)
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
            await self._update_task_status(task, MigrationStatus.CANCELLED)
            self._cancel_flags.pop(task_id, None)
            yield self._make_progress(task, bytes_transferred=transferred[0], message="cancelled")
            return
        except Exception:
            self._cleanup_target(target_handler, target_fs)
            raise

        await self._update_task_status(task, MigrationStatus.COPY_DONE, bytes_transferred=task.file_size)
        yield self._make_progress(task, bytes_transferred=task.file_size, message="Copy completed")

    # ------------------------------------------------------------------
    # Phase: UPDATING_DB
    # ------------------------------------------------------------------

    async def _execute_db_update(self, task: MigrationTaskModel) -> None:
        await self._update_task_status(task, MigrationStatus.UPDATING_DB)

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

        await self._update_task_status(task, MigrationStatus.DB_UPDATED)

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
        await self._update_task_status(task, MigrationStatus.DELETING_SOURCE)

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

        await self._update_task_status(task, MigrationStatus.COMPLETED)
        return warning

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _update_task_status(
        self, task: MigrationTaskModel, status: MigrationStatus, **extra_fields
    ) -> None:
        task.status = status
        task.updated_at = time.time()
        for key, value in extra_fields.items():
            setattr(task, key, value)
        if status in TERMINAL_STATUSES:
            task.completed_at = time.time()
        await task.save()

    def _make_progress(
        self,
        task: MigrationTaskModel,
        bytes_transferred: int | None = None,
        message: str | None = None,
    ) -> MigrationProgressStatus:
        bt = bytes_transferred if bytes_transferred is not None else task.bytes_transferred
        total = task.file_size
        pct = (bt / total * 100) if total > 0 else 0
        return MigrationProgressStatus(
            task_id=str(task.id),
            status=task.status,
            bytes_transferred=bt,
            total_bytes=total,
            progress_percentage=round(pct, 1),
            message=message,
        )

    async def _is_actively_migrating(self, db_path: str) -> bool:
        active_statuses = [s.value for s in MigrationStatus if s not in TERMINAL_STATUSES]
        count = await MigrationTaskModel.find(
            {
                "status": {"$in": active_statuses},
                "source_path": db_path,
            }
        ).count()
        return count > 0

    @staticmethod
    def _cleanup_target(handler: BaseResourceHandler, target_fs: str) -> None:
        try:
            if handler.file_exists(target_fs):
                handler.delete_file(target_fs)
        except Exception as e:
            logger.warning(f"Failed to cleanup target file {target_fs}: {e}")

    @staticmethod
    def _generate_unique_name(handler: BaseResourceHandler, dir_fs: str, filename: str) -> str:
        name_no_ext = handler.get_filename_without_extension(filename)
        ext = handler.get_file_extension(filename)
        suffix = f".{ext}" if ext else ""
        counter = 1
        while True:
            candidate = handler.join_path(dir_fs, f"{name_no_ext}({counter}){suffix}")
            if not handler.file_exists(candidate):
                return candidate
            counter += 1