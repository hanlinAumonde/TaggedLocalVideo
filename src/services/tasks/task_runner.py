import asyncio
from contextlib import suppress
from typing import AsyncGenerator, NamedTuple

from src.db.models.MigrationTask_model import TaskStatus
from src.logger import get_logger
from src.services.tasks.state_machine import MigrationProgressStatus, StateMachine

logger = get_logger("task_runner")

_END_OF_STREAM = object()

class _QueuedJob(NamedTuple):
    """
    One unit of work waiting in the job queue.

    :param task_id: String form of the task's ObjectId.
    :type task_id: str
    :param executor_key: Which registered executor should run it.
    :type executor_key: str
    :param start_from: Phase to resume at; earlier phases are skipped.
    :type start_from: TaskStatus
    """
    task_id: str
    executor_key: str
    start_from: TaskStatus


class TaskRunner:
    """
    Process-wide background job runner.

    Execution is fully decoupled from any client connection: work is submitted to a FIFO
    queue, a fixed pool of workers drains it, and progress is fanned out to any number of
    observers. Observing is a side-effect-free read, so a client may attach, detach and
    re-attach freely without disturbing the job.

    Two different kinds of queue live in here — keep them apart when reading:

    * ``_job_queue`` — ONE queue of pending work, shared by all workers. Carries
      _QueuedJob tickets. This is the scheduling side.
    * ``_observer_channels[task_id]`` — ONE queue PER WATCHING CLIENT, carrying progress
      frames out to that client. This is the notification side. A task being watched by
      three browser tabs has three channels.
    """

    def __init__(self, max_concurrent: int = 2):
        """
        :param max_concurrent: How many tasks may run at once. Becomes the size of the
            worker pool, so it is also the number of coroutines started by ``start()``.
            Clamped to at least 1.
        :type max_concurrent: int
        """
        self._max_concurrent = max(1, max_concurrent)
        self._executors: dict[str, StateMachine] = {}

        # Scheduling: pending work, and the workers that consume it.
        self._job_queue: asyncio.Queue[_QueuedJob] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []

        # Where each task currently is. Used both to reject duplicate submissions and to
        # tell observers whether there is anything left to wait for.
        self._waiting_task_ids: set[str] = set()
        self._running_task_ids: set[str] = set()

        # Notification: most recent frame per task, and the live observer channels.
        self._latest_progress: dict[str, MigrationProgressStatus] = {}
        self._observer_channels: dict[str, set[asyncio.Queue]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def register_executor(self, key: str, executor: StateMachine) -> None:
        """
        Make an executor available to ``submit`` and ``recover``.

        Keeps the runner independent of any particular task type: adding a new kind of
        background job means writing another ``StateMachine`` and registering it here.

        :param key: Name callers pass as ``executor_key``, e.g. ``"migration"``.
        :type key: str
        :param executor: The state machine that knows how to run this kind of task.
        :type executor: StateMachine
        :rtype: None
        """
        self._executors[key] = executor

    def start(self) -> None:
        """
        Start the worker pool. Idempotent — a second call while workers exist does nothing.

        :rtype: None
        """
        if self._workers:
            return
        for i in range(self._max_concurrent):
            self._workers.append(asyncio.create_task(self._worker(i), name=f"task-worker-{i}"))
        logger.info(f"TaskRunner started with {self._max_concurrent} worker(s)")

    async def shutdown(self) -> None:
        """
        Stop the worker pool and release every observer.

        Deliberately does not wait for in-flight tasks: a migration can run for many
        minutes, and interrupted tasks are picked back up by ``recover()`` on the next
        startup. Cancelling a worker propagates into its state machine, which leaves the
        persisted status untouched precisely so recovery can resume it.

        :rtype: None
        """
        for worker in self._workers:
            worker.cancel()
        for worker in self._workers:
            with suppress(asyncio.CancelledError):
                await worker
        self._workers.clear()
        for task_id in list(self._observer_channels):
            self._end_observer_streams(task_id)
        logger.info("TaskRunner stopped")

    async def recover(self) -> None:
        """
        Re-queue tasks abandoned by a previous process run.

        Asks every registered executor to plan its own recovery, then submits what comes
        back. Call once at startup. A planning failure is logged and skipped rather than
        raised, so one broken executor cannot stop the application from booting.

        :rtype: None
        """
        for key, executor in self._executors.items():
            try:
                plan = await executor.plan_recovery()
            except Exception as e:
                logger.exception(f"Recovery planning failed for executor '{key}': {e}")
                continue
            for task_id, start_from in plan:
                await self.submit(task_id, executor_key=key, start_from=start_from)
            if plan:
                logger.info(f"Recovered {len(plan)} '{key}' task(s)")

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    async def submit(
        self,
        task_id: str,
        executor_key: str = "migration",
        start_from: TaskStatus = TaskStatus.PROCESSING,
    ) -> None:
        """
        Queue a task for execution and return at once, without waiting for it to run.

        Submitting a task that is already queued or running is ignored, which is what keeps
        a retry and a crash recovery from starting the same job twice.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :param executor_key: Which registered executor should run it.
        :type executor_key: str
        :param start_from: Phase to resume at. Defaults to running the task in full.
        :type start_from: TaskStatus
        :rtype: None
        :raises KeyError: If no executor is registered under ``executor_key``.
        """
        if executor_key not in self._executors:
            raise KeyError(f"No executor registered under '{executor_key}'")
        if self.is_active(task_id):
            logger.debug(f"Task {task_id} is already active, ignoring duplicate submit")
            return

        self._waiting_task_ids.add(task_id)
        await self._job_queue.put(_QueuedJob(task_id, executor_key, start_from))
        logger.info(f"Task {task_id} queued (resume from {start_from})")

    def is_active(self, task_id: str) -> bool:
        """
        Report whether the task is still under this runner's care.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :return: True while the task is waiting in the queue or running in a worker.
        :rtype: bool
        """
        return task_id in self._waiting_task_ids or task_id in self._running_task_ids

    async def wait_idle(self) -> None:
        """
        Block until the job queue is empty and every dequeued job has finished.

        Backed by the ``task_done()`` call in the worker loop. Not used on the request
        path — the app never waits on background work — but it is how tests synchronise
        with the pool deterministically.

        :rtype: None
        """
        await self._job_queue.join()

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    async def observe(
        self, task_id: str, executor_key: str = "migration"
    ) -> AsyncGenerator[MigrationProgressStatus, None]:
        """
        Yield progress frames for a task until it settles.

        A pure read: attaching never starts, restarts or otherwise affects the job, so a
        client may refresh, navigate away and come back, or watch from several tabs at
        once. Detaching only removes that client's channel.

        The stream opens with the task's current state — the last live frame if one is
        held, otherwise a snapshot rebuilt from the database — so a reconnecting client
        sees progress immediately instead of waiting for the next update. It then follows
        live frames until the task settles, and completes.

        Ordering matters in the implementation: the channel is registered *before* the
        liveness check, so a task settling at that exact moment still delivers its
        end-of-stream marker instead of leaving the observer waiting forever.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :param executor_key: Executor to ask for the fallback snapshot.
        :type executor_key: str
        :yield: Progress frames, starting with the current state.
        :rtype: AsyncGenerator[MigrationProgressStatus, None]
        """
        channel: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._observer_channels.setdefault(task_id, set()).add(channel)

        try:
            # Open with the current state so a reconnecting client sees progress at once
            # rather than waiting for the next frame.
            snapshot = self._latest_progress.get(task_id)
            if snapshot is None:
                executor = self._executors.get(executor_key)
                if executor is not None:
                    snapshot = await executor.build_snapshot(task_id)
            if snapshot is not None:
                yield snapshot

            if not self.is_active(task_id):
                return

            while True:
                frame = await channel.get()
                if frame is _END_OF_STREAM:
                    return
                yield frame
        finally:
            channels = self._observer_channels.get(task_id)
            if channels is not None:
                channels.discard(channel)
                if not channels:
                    self._observer_channels.pop(task_id, None)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _worker(self, worker_index: int) -> None:
        """
        Consume jobs from the queue, one at a time, forever.

        Running exactly ``max_concurrent`` of these *is* the concurrency limit — no
        semaphore involved. A job that raises is logged and the loop continues, since
        letting one bad task kill a worker would permanently shrink the pool.

        :param worker_index: Position in the pool, for log messages.
        :type worker_index: int
        :rtype: None
        :raises asyncio.CancelledError: On shutdown, after the current job's cleanup runs.
        """
        while True:
            job = await self._job_queue.get()
            self._waiting_task_ids.discard(job.task_id)
            self._running_task_ids.add(job.task_id)
            try:
                await self._run_and_broadcast(
                    self._executors[job.executor_key], job.task_id, job.start_from
                )
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_index} cancelled while running task {job.task_id}")
                raise
            except Exception as e:
                logger.exception(f"Task {job.task_id} crashed outside the state machine: {e}")
            finally:
                self._running_task_ids.discard(job.task_id)
                self._end_observer_streams(job.task_id)
                # Balances the get() above; what makes wait_idle() work.
                self._job_queue.task_done()

    async def _run_and_broadcast(
        self, executor: StateMachine, task_id: str, start_from: TaskStatus
    ) -> None:
        """
        Drive the state machine and push every frame it emits out to observers.

        This ``async for`` is the whole point of the redesign: it lives in a worker
        coroutine owned by the app lifespan, not in a subscription's generator, so a
        client disconnecting cannot halt the task.

        :param executor: The state machine to run.
        :type executor: StateMachine
        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :param start_from: Phase to resume at.
        :type start_from: TaskStatus
        :rtype: None
        """
        async for frame in executor.run_task(task_id, start_from=start_from):
            self._latest_progress[task_id] = frame
            self._broadcast(task_id, frame)

    def _broadcast(self, task_id: str, frame) -> None:
        """
        Fan one frame out to every observer of this task.

        Deliberately synchronous: with no await inside, an observer detaching cannot mutate
        the channel set mid-iteration, so no lock is needed.

        A full channel means that observer is falling behind; its oldest frame is dropped
        to make room. Losing an intermediate percentage is harmless — clients only care
        about the newest one — whereas blocking here would stall the actual transfer.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :param frame: The progress frame to deliver.
        :type frame: MigrationProgressStatus
        :rtype: None
        """
        for channel in self._observer_channels.get(task_id, set()):
            if channel.full():
                # Observer is lagging; drop its oldest frame rather than block the job.
                with suppress(asyncio.QueueEmpty):
                    channel.get_nowait()
            with suppress(asyncio.QueueFull):
                channel.put_nowait(frame)

    def _end_observer_streams(self, task_id: str) -> None:
        """
        Tell every observer of this task that no further frames are coming.

        Called from the worker's ``finally``, so it also fires when a task crashes or the
        process shuts down — an observer must never be left waiting on a stream that has
        stopped producing.

        :param task_id: String form of the task's ObjectId.
        :type task_id: str
        :rtype: None
        """
        for channel in self._observer_channels.get(task_id, set()):
            with suppress(asyncio.QueueFull):
                channel.put_nowait(_END_OF_STREAM)
