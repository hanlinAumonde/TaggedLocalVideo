from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from time import time
from typing import AsyncGenerator

from src.db.models.MigrationTask_model import TaskStatus, MigrationTaskModel
from src.logger import get_logger
from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.base_resource_handler import BaseResourceHandler
from src.services.resource_handler.resource_handler_service import ResourceHandlerService

logger = get_logger("migration_state_machine")

@dataclass
class MigrationProgressStatus:
    task_id: str
    status: str
    bytes_transferred: int
    total_bytes: int
    progress_percentage: float
    message: str | None = None

    
class StateMachine(ABC):

    _PHASE_ORDER = [TaskStatus.PROCESSING, TaskStatus.UPDATING_DB, TaskStatus.DELETING_SOURCE]
    TERMINAL_STATUSES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

    def __init__(
            self,
            resource_handler_service: ResourceHandlerService,
            dir_metadata_service: DirMetadataService,
        ):
            self.resourceHandlerService = resource_handler_service
            self.dirMetadataService = dir_metadata_service
            self._cancel_flags: dict[str, bool] = {}

    async def _run_state_machine(
            self,
            task: MigrationTaskModel,
            start_from: TaskStatus,
        ) -> AsyncGenerator[MigrationProgressStatus, None]:
            source_handler = self.resourceHandlerService.get_handler(task.source_category)
            target_handler = self.resourceHandlerService.get_handler(task.target_category)
    
            source_fs = source_handler.convert_to_FS_format_path(task.source_path)
            target_db = task.renamed_target_path or task.target_path
            target_fs = target_handler.convert_to_FS_format_path(target_db)
    
            try:
                if self._should_run_phase(start_from, TaskStatus.PROCESSING):
                    async for progress in self._execute_processing(
                        task, source_handler, target_handler, source_fs, target_fs
                    ):
                        yield progress
                    if task.status == TaskStatus.CANCELLED:
                        return
    
                if self._should_run_phase(start_from, TaskStatus.UPDATING_DB):
                    await self._execute_db_update(task)
                    yield self._make_progress(task, message="Database updated")
    
                if self._should_run_phase(start_from, TaskStatus.DELETING_SOURCE):
                    warning = await self._execute_delete_source(
                        task, source_handler, target_handler, source_fs
                    )
                    yield self._make_progress(task, message=warning or "Migration completed")
    
            except Exception as e:
                logger.exception(f"Migration task {task.id} failed: {e}")
                failed_step = task.status if task.status not in StateMachine.TERMINAL_STATUSES else TaskStatus.PROCESSING
                await self._update_task_status(
                    task,
                    TaskStatus.FAILED,
                    error_message=str(e),
                    failed_step=str(failed_step),
                )
                yield self._make_progress(task, message=f"Migration failed: {e}")

    @staticmethod
    def _should_run_phase(start_from: TaskStatus, phase: TaskStatus) -> bool:
        order = {s: i for i, s in enumerate(StateMachine._PHASE_ORDER)}
        return order.get(phase, 0) >= order.get(start_from, 0)

    # ------------------------------------------------------------------
    # Phase: PROCESSING
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute_processing(self,
         task: MigrationTaskModel,
         source_handler: BaseResourceHandler,
         target_handler: BaseResourceHandler,
         source_fs: str,
         target_fs: str
    ) -> AsyncGenerator[MigrationProgressStatus, None]:
        ...

    # ------------------------------------------------------------------
    # Phase: UPDATING_DB
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute_db_update(self, task: MigrationTaskModel) -> None:
        ...

    # ------------------------------------------------------------------
    # Phase: DELETING_SOURCE
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute_delete_source(
        self,
        task: MigrationTaskModel,
        source_handler: BaseResourceHandler,
        target_handler: BaseResourceHandler,
        source_fs: str,
    ) -> str | None:
        ...


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    
    async def _update_task_status(
        self, task: MigrationTaskModel, status: TaskStatus, **extra_fields
    ) -> None:
        task.status = status
        task.updated_at = time()
        for key, value in extra_fields.items():
            setattr(task, key, value)
        if status in StateMachine.TERMINAL_STATUSES:
            task.completed_at = time()
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
        active_statuses = [s.value for s in TaskStatus if s not in StateMachine.TERMINAL_STATUSES]
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

    