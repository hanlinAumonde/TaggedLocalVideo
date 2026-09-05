from abc import ABC, abstractmethod
import asyncio
from time import time
from typing import AsyncGenerator, Generic, TypeVar

from bson import ObjectId

from src.logger import get_logger
from src.platform.jobs.progress import ProgressFrame
from src.platform.jobs.task_model import BaseTaskModel, TaskStatus

logger = get_logger("task_state_machine")

TTask = TypeVar("TTask", bound=BaseTaskModel)


class TaskStateMachine(ABC, Generic[TTask]):
    """
    Lifecycle template for a background task that runs in three phases.

    The phases are deliberately coarse, because they are the ones that decide how far a
    crashed task has to be rewound:

    1. ``PROCESSING`` — do the actual work, reporting progress as it goes.
    2. ``UPDATING_DB`` — make the database reflect the result.
    3. ``DELETING_SOURCE`` — settle the outside world, e.g. remove what the work replaced.

    A task type that has nothing to do in a phase implements it as a no-op; the ordering
    and the crash-recovery matrix still hold. What the template owns is *when* phases run,
    how failure is distinguished from shutdown, and how progress is throttled to the
    database. What it deliberately knows nothing about is the work itself — no storage, no
    paths, no particular document class.

    Subclasses bind their document type by declaring ``task_model``::

        class ReindexStateMachine(TaskStateMachine[ReindexTaskModel]):
            task_model = ReindexTaskModel
    """

    #: Document class this machine drives. Every subclass must set it.
    task_model: type[TTask]

    _PHASE_ORDER = [TaskStatus.PROCESSING, TaskStatus.UPDATING_DB, TaskStatus.DELETING_SOURCE]
    TERMINAL_STATUSES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

    # Where a task interrupted mid-flight should resume from, given the status it died in.
    # Phases that may have left partial side effects resume at their own start and rely on
    # _compensate_before_resume to undo them first.
    _RESUME_POINT_BY_STATUS = {
        TaskStatus.PENDING: TaskStatus.PROCESSING,
        TaskStatus.PROCESSING: TaskStatus.PROCESSING,
        TaskStatus.PROCESS_DONE: TaskStatus.UPDATING_DB,
        TaskStatus.UPDATING_DB: TaskStatus.UPDATING_DB,
        TaskStatus.DB_UPDATED: TaskStatus.DELETING_SOURCE,
        TaskStatus.DELETING_SOURCE: TaskStatus.DELETING_SOURCE,
    }

    def __init__(self, progress_flush_interval: float = 3.0):
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
    ) -> AsyncGenerator[ProgressFrame, None]:
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
        :rtype: AsyncGenerator[ProgressFrame, None]
        """
        task = await self.task_model.get(ObjectId(task_id))
        if task is None:
            logger.warning(f"Task {task_id} no longer exists, skipping execution")
            return

        if task.status in TaskStateMachine.TERMINAL_STATUSES:
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

        Cooperative, not immediate: a running phase polls this flag, and ``run_task``
        checks it before starting a task that is still queued.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        """
        self._cancel_requested[task_id] = True

    async def build_snapshot(self, task_id: str) -> ProgressFrame | None:
        """
        Build a progress frame from persisted state.

        Used by ``TaskRunner.observe`` when no live frame is held in memory — for example
        after a process restart, or for a task that finished long ago.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :return: A frame describing the task's stored state, or None if it no longer exists.
        :rtype: ProgressFrame | None
        """
        task = await self.task_model.get(ObjectId(task_id))
        if task is None:
            return None
        return self._make_progress(task)

    async def plan_recovery(self) -> list[tuple[str, TaskStatus]]:
        """
        Work out how to resume tasks abandoned by a previous process run.

        Any task left in a non-terminal status means the process died mid-flight. Each is
        mapped through ``_RESUME_POINT_BY_STATUS`` to the phase it should restart at, given
        a chance to undo its partial side effects via ``_compensate_before_resume``, then
        reset to PENDING so the task list shows it as queued rather than falsely running.

        Called once at startup, before any worker begins consuming the queue.

        :return: ``(task_id, start_from)`` pairs ready to hand to ``TaskRunner.submit``.
        :rtype: list[tuple[str, TaskStatus]]
        """
        active_statuses = [
            s.value for s in TaskStatus if s not in TaskStateMachine.TERMINAL_STATUSES
        ]
        orphans = await self.task_model.find({"status": {"$in": active_statuses}}).to_list()

        plan: list[tuple[str, TaskStatus]] = []
        for task in orphans:
            status = TaskStatus(task.status)
            start_from = TaskStateMachine._RESUME_POINT_BY_STATUS.get(status)
            if start_from is None:
                logger.warning(f"Task {task.id} has unrecoverable status {status}, leaving as is")
                continue

            try:
                await self._compensate_before_resume(task, start_from)
            except Exception as e:
                logger.warning(f"Task {task.id}: compensation before resume failed: {e}")

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
        task: TTask,
        start_from: TaskStatus,
    ) -> AsyncGenerator[ProgressFrame, None]:
        """
        Drive the three phases in order, skipping any that precede ``start_from``.

        Failure handling differs by cause, and the distinction matters:

        * ``CancelledError`` (process shutting down) — the persisted status is left
          untouched and the error re-raised, so ``plan_recovery`` picks the task up on
          the next startup.
        * Any other exception — the task is marked FAILED with ``failed_step`` set to
          the phase that broke, which is what lets a later retry resume from there.

        :param task: The task document, already loaded and known to be non-terminal.
        :type task: TTask
        :param start_from: First phase to execute.
        :type start_from: TaskStatus
        :yield: Progress frames from each phase.
        :rtype: AsyncGenerator[ProgressFrame, None]
        :raises asyncio.CancelledError: Propagated on shutdown so the worker can stop.
        """
        try:
            if self._should_run_phase(start_from, TaskStatus.PROCESSING):
                async for progress in self._execute_processing(task):
                    yield progress
                if task.status == TaskStatus.CANCELLED:
                    return

            if self._should_run_phase(start_from, TaskStatus.UPDATING_DB):
                await self._execute_db_update(task)
                yield self._make_progress(task, message="Database updated")

            if self._should_run_phase(start_from, TaskStatus.DELETING_SOURCE):
                warning = await self._execute_fs_cleanup(task)
                yield self._make_progress(task, message=warning or "Task completed")

        except asyncio.CancelledError:
            # Process is shutting down. Leave the persisted status alone so that
            # plan_recovery() can resume this task on the next startup.
            logger.info(f"Task {task.id} interrupted at {task.status}, will recover on restart")
            raise

        except Exception as e:
            logger.exception(f"Task {task.id} failed: {e}")
            failed_step = (
                task.status
                if task.status not in TaskStateMachine.TERMINAL_STATUSES
                else TaskStatus.PROCESSING
            )
            await self._update_task_status(
                task,
                TaskStatus.FAILED,
                error_message=str(e),
                failed_step=TaskStatus(failed_step).value,
            )
            yield self._make_progress(task, message=f"Task failed: {e}")

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
        order = {s: i for i, s in enumerate(TaskStateMachine._PHASE_ORDER)}
        return order.get(phase, 0) >= order.get(start_from, 0)

    # ------------------------------------------------------------------
    # Phases — implemented per task type
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute_processing(self, task: TTask) -> AsyncGenerator[ProgressFrame, None]:
        """
        Phase 1 — do the work, reporting progress as it goes.

        Implementations must poll ``_cancel_requested`` if they can run for a long time,
        and must undo their partial side effects before propagating an error, since this
        phase always restarts from the beginning on both retry and crash recovery.

        :param task: The task being executed.
        :type task: TTask
        :yield: Progress frames while the work is in flight.
        :rtype: AsyncGenerator[ProgressFrame, None]
        """
        ...

    @abstractmethod
    async def _execute_db_update(self, task: TTask) -> None:
        """
        Phase 2 — make the database reflect the completed work.

        Must be idempotent: recovery may run this phase again after it already succeeded,
        so implementations have to detect and tolerate work that is already done.

        :param task: The task being executed.
        :type task: TTask
        :rtype: None
        """
        ...

    @abstractmethod
    async def _execute_fs_cleanup(self, task: TTask) -> str | None:
        """
        Phase 3 — settle the outside world and finish the task.

        Failures here are reported rather than raised: by this point the work is done and
        the database already records it, so a leftover file or a stale aggregate is worth a
        warning, not a failure. Implementations end by marking the task COMPLETED.

        A task type with nothing to clean up implements this as ``return None``.

        :param task: The task being executed.
        :type task: TTask
        :return: A warning to surface to the user, or None if everything went cleanly.
        :rtype: str | None
        """
        ...

    async def _compensate_before_resume(self, task: TTask, start_from: TaskStatus) -> None:
        """
        Undo the partial side effects of an interrupted phase, before it is re-run.

        Called by ``plan_recovery`` for every task being resumed, and available to retry
        paths that rewind a task the same way. The default does nothing, which is correct
        for any task whose phases leave nothing behind when they die halfway.

        Exceptions are logged and swallowed by the caller: a task that cannot be tidied up
        should still be recovered rather than stranded.

        :param task: The task about to be re-queued.
        :type task: TTask
        :param start_from: The phase it will resume at.
        :type start_from: TaskStatus
        :rtype: None
        """
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _update_task_status(self, task: TTask, status: TaskStatus, **extra_fields) -> None:
        """
        Move the task to a new status and persist it, stamping ``completed_at`` on
        terminal statuses.

        :param task: The task document to update in place.
        :type task: TTask
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
        if status in TaskStateMachine.TERMINAL_STATUSES:
            task.completed_at = time()
        await task.save()

    async def _maybe_flush_progress(self, task: TTask, current: int) -> None:
        """
        Persist progress, at most once per ``progress_flush_interval``.

        Throttled because a running phase reports far more often than the database needs to
        know. Also refreshes ``updated_at``, which doubles as a liveness marker for the task.

        :param task: The task document to update in place.
        :type task: TTask
        :param current: Work done so far, in the task's own progress unit.
        :type current: int
        :rtype: None
        """
        task_id = str(task.id)
        now = time()
        if now - self._last_flush_at.get(task_id, 0.0) < self._progress_flush_interval:
            return
        self._last_flush_at[task_id] = now
        task.set_progress(current)
        task.updated_at = now
        await task.save()

    def _make_progress(
        self,
        task: TTask,
        current: int | None = None,
        message: str | None = None,
    ) -> ProgressFrame:
        """
        Build a progress frame from a task's current state.

        Reads through the model's progress accessors rather than any particular field, so
        the template works for tasks that measure something other than bytes.

        :param task: The task to describe.
        :type task: TTask
        :param current: Live progress count. Falls back to the persisted value when
            omitted, which is what phases outside the main work loop rely on.
        :type current: int | None
        :param message: Optional note to attach to the frame.
        :type message: str | None
        :return: The assembled frame; percentage is derived by the frame itself.
        :rtype: ProgressFrame
        """
        stored_current, total = task.get_progress()
        return ProgressFrame(
            task_id=str(task.id),
            status=task.status,
            current=stored_current if current is None else current,
            total=total,
            message=message,
        )
