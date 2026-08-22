from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from time import time
from typing import AsyncGenerator

from bson import ObjectId

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

    # Where a task interrupted mid-flight should resume from. PROCESSING requires the
    # partially written target file to be cleaned up first (see plan_recovery).
    _RESUME_POINT_BY_STATUS = {
        TaskStatus.PENDING: TaskStatus.PROCESSING,
        TaskStatus.PROCESSING: TaskStatus.PROCESSING,
        TaskStatus.PROCESS_DONE: TaskStatus.UPDATING_DB,
        TaskStatus.UPDATING_DB: TaskStatus.UPDATING_DB,
        TaskStatus.DB_UPDATED: TaskStatus.DELETING_SOURCE,
        TaskStatus.DELETING_SOURCE: TaskStatus.DELETING_SOURCE,
    }

    def __init__(
            self,
            resource_handler_service: ResourceHandlerService,
            dir_metadata_service: DirMetadataService,
            progress_flush_interval: float = 3.0,
        ):
            self.resourceHandlerService = resource_handler_service
            self.dirMetadataService = dir_metadata_service
            self._progress_flush_interval = progress_flush_interval

            # task_id -> True once someone asked for this task to stop. 
            self._cancel_requested: dict[str, bool] = {}
            # task_id -> timestamp of the last progress write, for throttling.
            self._last_flush_at: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Runner-facing API
    # ------------------------------------------------------------------

    async def run_task(
        self,
        task_id: str,
        start_from: TaskStatus = TaskStatus.PROCESSING,
    ) -> AsyncGenerator[MigrationProgressStatus, None]:
        """
        Execute a task, yielding a progress frame at every notable step.

        Called only by ``TaskRunner``'s worker loop. Deliberately forgiving: a task that
        has vanished or already settled produces no frames rather than raising, so that a
        stale queue entry can never crash a worker.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :param start_from: Phase to resume at. Earlier phases are skipped, which is how a
            recovered or retried task avoids redoing work it already completed.
        :type start_from: TaskStatus
        :yield: Progress frames, ending with a terminal-status frame on failure or
            cancellation.
        :rtype: AsyncGenerator[MigrationProgressStatus, None]
        """
        task = await MigrationTaskModel.get(ObjectId(task_id))
        if task is None:
            logger.warning(f"Task {task_id} no longer exists, skipping execution")
            return

        if task.status in StateMachine.TERMINAL_STATUSES:
            logger.info(f"Task {task_id} is already {task.status}, skipping execution")
            self._cancel_requested.pop(task_id, None)
            return

        # Cancelled while sitting in the queue.
        if self._cancel_requested.pop(task_id, False):
            await self._update_task_status(task, TaskStatus.CANCELLED)
            yield self._make_progress(task, message="cancelled")
            return

        try:
            async for progress in self._run_state_machine(task, start_from=start_from):
                yield progress
        finally:
            self._last_flush_at.pop(task_id, None)
            self._cancel_requested.pop(task_id, None)

    def request_cancel(self, task_id: str) -> None:
        """
        Ask a task to stop at its next checkpoint.

        Cooperative, not immediate: the copy loop polls this flag once per chunk, and
        ``run_task`` checks it before starting a task that is still queued.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        """
        self._cancel_requested[task_id] = True

    async def build_snapshot(self, task_id: str) -> MigrationProgressStatus | None:
        """
        Build a progress frame from persisted state.

        Used by ``TaskRunner.observe`` when no live frame is held in memory — for example
        after a process restart, or for a task that finished long ago.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :return: A frame describing the task's stored state, or None if it no longer exists.
        :rtype: MigrationProgressStatus | None
        """
        task = await MigrationTaskModel.get(ObjectId(task_id))
        if task is None:
            return None
        return self._make_progress(task)

    async def plan_recovery(self) -> list[tuple[str, TaskStatus]]:
        """
        Work out how to resume tasks abandoned by a previous process run.

        Any task left in a non-terminal status means the process died mid-flight. Each is
        mapped through ``_RESUME_POINT_BY_STATUS`` to the phase it should restart at, then
        reset to PENDING so the task list shows it as queued rather than falsely running.
        Tasks interrupted during the copy also get their half-written target file removed
        and their byte counter zeroed, so the copy can start clean.

        Called once at startup, before any worker begins consuming the queue.

        :return: ``(task_id, start_from)`` pairs ready to hand to ``TaskRunner.submit``.
        :rtype: list[tuple[str, TaskStatus]]
        """
        active_statuses = [s.value for s in TaskStatus if s not in StateMachine.TERMINAL_STATUSES]
        orphans = await MigrationTaskModel.find({"status": {"$in": active_statuses}}).to_list()

        plan: list[tuple[str, TaskStatus]] = []
        for task in orphans:
            status = TaskStatus(task.status)
            start_from = StateMachine._RESUME_POINT_BY_STATUS.get(status)
            if start_from is None:
                logger.warning(f"Task {task.id} has unrecoverable status {status}, leaving as is")
                continue

            if start_from == TaskStatus.PROCESSING:
                try:
                    target_handler = self.resourceHandlerService.get_handler(task.target_category)
                    target_db = task.renamed_target_path or task.target_path
                    self._cleanup_target(
                        target_handler, target_handler.convert_to_FS_format_path(target_db)
                    )
                except Exception as e:
                    logger.warning(f"Task {task.id}: failed to clean up partial target: {e}")
                task.bytes_transferred = 0

            task.status = TaskStatus.PENDING
            task.updated_at = time()
            await task.save()

            logger.info(f"Recovering task {task.id}: {status} -> resume from {start_from}")
            plan.append((str(task.id), start_from))

        return plan

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    async def _run_state_machine(
            self,
            task: MigrationTaskModel,
            start_from: TaskStatus,
        ) -> AsyncGenerator[MigrationProgressStatus, None]:
            """
            Drive the three phases in order, skipping any that precede ``start_from``.

            Failure handling differs by cause, and the distinction matters:

            * ``CancelledError`` (process shutting down) — the persisted status is left
              untouched and the error re-raised, so ``plan_recovery`` picks the task up on
              the next startup.
            * Any other exception — the task is marked FAILED with ``failed_step`` set to
              the phase that broke, which is what lets a later retry resume from there.

            :param task: The task document, already loaded and known to be non-terminal.
            :type task: MigrationTaskModel
            :param start_from: First phase to execute.
            :type start_from: TaskStatus
            :yield: Progress frames from each phase.
            :rtype: AsyncGenerator[MigrationProgressStatus, None]
            :raises asyncio.CancelledError: Propagated on shutdown so the worker can stop.
            """
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

            except asyncio.CancelledError:
                # Process is shutting down. Leave the persisted status alone so that
                # plan_recovery() can resume this task on the next startup.
                logger.info(f"Migration task {task.id} interrupted at {task.status}, will recover on restart")
                raise

            except Exception as e:
                logger.exception(f"Migration task {task.id} failed: {e}")
                failed_step = task.status if task.status not in StateMachine.TERMINAL_STATUSES else TaskStatus.PROCESSING
                await self._update_task_status(
                    task,
                    TaskStatus.FAILED,
                    error_message=str(e),
                    failed_step=TaskStatus(failed_step).value,
                )
                yield self._make_progress(task, message=f"Migration failed: {e}")

    @staticmethod
    def _should_run_phase(start_from: TaskStatus, phase: TaskStatus) -> bool:
        """
        Decide whether a phase is at or after the resume point.

        Statuses that are not phases themselves (PROCESS_DONE, DB_UPDATED, ...) fall back
        to position 0, so an unmapped ``start_from`` conservatively runs everything.

        :param start_from: The phase execution should resume at.
        :type start_from: TaskStatus
        :param phase: The phase being considered.
        :type phase: TaskStatus
        :return: True if ``phase`` should run.
        :rtype: bool
        """
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
        """
        Phase 1 — move the bytes, reporting progress as they go.

        Implementations must poll ``_cancel_requested`` and must remove any partially
        written target file before propagating an error, since this phase is restarted
        from scratch on both retry and crash recovery.

        :param task: The task being executed.
        :type task: MigrationTaskModel
        :param source_handler: Storage handler for the source category.
        :type source_handler: BaseResourceHandler
        :param target_handler: Storage handler for the target category.
        :type target_handler: BaseResourceHandler
        :param source_fs: Source path in FS format (filesystem path or object key).
        :type source_fs: str
        :param target_fs: Target path in FS format, already resolved for any rename.
        :type target_fs: str
        :yield: Progress frames during the transfer.
        :rtype: AsyncGenerator[MigrationProgressStatus, None]
        """
        ...

    # ------------------------------------------------------------------
    # Phase: UPDATING_DB
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute_db_update(self, task: MigrationTaskModel) -> None:
        """
        Phase 2 — point the database records at the new location.

        Must be idempotent: recovery may run this phase again after it already succeeded,
        so implementations have to detect and tolerate work that is already done.

        :param task: The task being executed.
        :type task: MigrationTaskModel
        :rtype: None
        """
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
        """
        Phase 3 — remove the original and settle the task.

        Failures here are reported rather than raised: by this point the file has been
        copied and the database updated, so the migration has effectively succeeded and a
        leftover source file should not undo it.

        :param task: The task being executed.
        :type task: MigrationTaskModel
        :param source_handler: Storage handler for the source category.
        :type source_handler: BaseResourceHandler
        :param target_handler: Storage handler for the target category.
        :type target_handler: BaseResourceHandler
        :param source_fs: Source path in FS format.
        :type source_fs: str
        :return: A warning to surface to the user, or None if everything went cleanly.
        :rtype: str | None
        """
        ...


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _update_task_status(
        self, task: MigrationTaskModel, status: TaskStatus, **extra_fields
    ) -> None:
        """
        Move the task to a new status and persist it, stamping ``completed_at`` on
        terminal statuses.

        :param task: The task document to update in place.
        :type task: MigrationTaskModel
        :param status: The status to move to.
        :type status: TaskStatus
        :param extra_fields: Additional document fields to set in the same write, e.g.
            ``error_message`` or ``failed_step``.
        :rtype: None
        """
        task.status = status
        task.updated_at = time()
        for key, value in extra_fields.items():
            setattr(task, key, value)
        if status in StateMachine.TERMINAL_STATUSES:
            task.completed_at = time()
        await task.save()

    async def _maybe_flush_progress(self, task: MigrationTaskModel, bytes_transferred: int) -> None:
        """
        Persist copy progress, at most once per ``progress_flush_interval``.

        Throttled because the copy loop reports far more often than the database needs to
        know. Also refreshes ``updated_at``, which doubles as a liveness marker for the task.

        :param task: The task document to update in place.
        :type task: MigrationTaskModel
        :param bytes_transferred: Bytes copied so far.
        :type bytes_transferred: int
        :rtype: None
        """
        task_id = str(task.id)
        now = time()
        if now - self._last_flush_at.get(task_id, 0.0) < self._progress_flush_interval:
            return
        self._last_flush_at[task_id] = now
        task.bytes_transferred = bytes_transferred
        task.updated_at = now
        await task.save()

    def _make_progress(
        self,
        task: MigrationTaskModel,
        bytes_transferred: int | None = None,
        message: str | None = None,
    ) -> MigrationProgressStatus:
        """
        Build a progress frame from a task's current state.

        :param task: The task to describe.
        :type task: MigrationTaskModel
        :param bytes_transferred: Live byte count. Falls back to the persisted value when
            omitted, which is what phases outside the copy loop rely on.
        :type bytes_transferred: int | None
        :param message: Optional note to attach to the frame.
        :type message: str | None
        :return: The assembled frame, with percentage computed and rounded.
        :rtype: MigrationProgressStatus
        """
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
        """
        Check whether a path is the source of a task that has not settled yet.

        Narrower than ``MigrationService.is_file_locked``, which also covers targets; this
        one answers "is this file already on its way out?".

        :param db_path: Path in DB format.
        :type db_path: str
        :return: True if a non-terminal task has this path as its source.
        :rtype: bool
        """
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
        """
        Delete a partially written target file, best effort.

        Never raises: this runs on paths that are already handling a cancellation, a
        failure or a crash recovery, where a cleanup problem must not mask the original
        cause.

        :param handler: Storage handler for the target category.
        :type handler: BaseResourceHandler
        :param target_fs: Target path in FS format.
        :type target_fs: str
        :rtype: None
        """
        try:
            if handler.file_exists(target_fs):
                handler.delete_file(target_fs)
        except Exception as e:
            logger.warning(f"Failed to cleanup target file {target_fs}: {e}")

    @staticmethod
    def _generate_unique_name(handler: BaseResourceHandler, dir_fs: str, filename: str) -> str:
        """
        Find a free ``name(n).ext`` variant in a directory, for the "rename" conflict
        strategy.

        :param handler: Storage handler for the directory's category.
        :type handler: BaseResourceHandler
        :param dir_fs: Target directory in FS format.
        :type dir_fs: str
        :param filename: Desired file name, including extension.
        :type filename: str
        :return: Full FS-format path of the first name not already taken.
        :rtype: str
        """
        name_no_ext = handler.get_filename_without_extension(filename)
        ext = handler.get_file_extension(filename)
        suffix = f".{ext}" if ext else ""
        counter = 1
        while True:
            candidate = handler.join_path(dir_fs, f"{name_no_ext}({counter}){suffix}")
            if not handler.file_exists(candidate):
                return candidate
            counter += 1
