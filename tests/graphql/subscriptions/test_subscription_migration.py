"""Tests for migration progress and retry subscriptions.

The subscriptions are observers over the background runner: progress must be read
from the runner, and opening one must never kick off execution itself.
"""

import pytest

from src.features.migration.migration_task import TaskStatus
from src.platform.jobs.progress import ProgressFrame
from src.schema.types.migration_type import MigrationProgressStatus
from src.features.migration.migration_service import MIGRATION_EXECUTOR_KEY
from tests.graphql.helpers import (
    MIGRATION_PROGRESS_SUBSCRIPTION,
    MIGRATION_RETRY_SUBSCRIPTION,
    assert_no_errors,
)

pytestmark = pytest.mark.subscription

TASK_ID = "507f1f77bcf86cd799439011"


async def _mock_progress_gen(*events):
    for e in events:
        yield e


def _events():
    return [
        ProgressFrame(
            task_id="tid", status="PROCESSING",
            current=50, total=100, message="Copying",
        ),
        ProgressFrame(
            task_id="tid", status="COMPLETED",
            current=100, total=100, message="Done",
        ),
    ]


class TestMigrationProgressSubscription:
    async def test_migration_progress_streams_events(
        self, subscribe_gql, mock_task_runner,
    ):
        mock_task_runner.observe.side_effect = (
            lambda *a, **kw: _mock_progress_gen(*_events())
        )

        results = await subscribe_gql(MIGRATION_PROGRESS_SUBSCRIPTION, {
            "input": {"taskId": TASK_ID}
        })
        assert len(results) == 2
        assert_no_errors(results[0])
        assert_no_errors(results[1])

        first = results[0].data["migrationProgressSubscription"]
        assert first["bytesTransferred"] == "50"
        assert first["progressPercentage"] == 50.0

        last = results[1].data["migrationProgressSubscription"]
        assert last["status"] == "COMPLETED"
        assert last["progressPercentage"] == 100.0

    async def test_progress_observes_and_never_submits(
        self, subscribe_gql, mock_task_runner,
    ):
        """Regression: a page refresh must not spawn a second copy of the same task."""
        mock_task_runner.observe.side_effect = (
            lambda *a, **kw: _mock_progress_gen(*_events())
        )

        await subscribe_gql(MIGRATION_PROGRESS_SUBSCRIPTION, {"input": {"taskId": TASK_ID}})

        mock_task_runner.observe.assert_called_once_with(
            TASK_ID, executor_key=MIGRATION_EXECUTOR_KEY
        )
        mock_task_runner.submit.assert_not_awaited()

    async def test_progress_on_settled_task_yields_nothing(
        self, subscribe_gql, mock_task_runner,
    ):
        """An already-finished task simply ends the stream instead of erroring."""
        results = await subscribe_gql(MIGRATION_PROGRESS_SUBSCRIPTION, {
            "input": {"taskId": TASK_ID}
        })
        assert results == []
        mock_task_runner.submit.assert_not_awaited()


class TestProgressFrameMapping:
    """The GraphQL layer keeps the byte-named fields the frontend already queries, even
    though the task template reports progress in generic units."""

    def test_generic_frame_maps_onto_the_published_byte_fields(self):
        frame = ProgressFrame(
            task_id="tid", status="PROCESSING", current=50, total=100, message="Copying",
        )

        published = MigrationProgressStatus.from_service(frame)

        assert published.bytes_transferred == 50
        assert published.total_bytes == 100
        assert published.progress_percentage == 50.0
        assert published.message == "Copying"

    def test_mapping_uses_the_frames_derived_percentage(self):
        """Percentage is computed once, on the frame, not recomputed per transport."""
        frame = ProgressFrame(task_id="tid", status="PROCESSING", current=1, total=3)

        assert MigrationProgressStatus.from_service(frame).progress_percentage == 33.3


class TestMigrationRetrySubscription:
    async def test_migration_retry_streams_events(
        self, subscribe_gql, mock_task_runner,
    ):
        mock_task_runner.observe.side_effect = (
            lambda *a, **kw: _mock_progress_gen(*_events())
        )

        results = await subscribe_gql(MIGRATION_RETRY_SUBSCRIPTION, {
            "input": {"taskId": TASK_ID}
        })
        assert len(results) == 2
        assert_no_errors(results[0])

        last = results[1].data["migrationRetrySubscription"]
        assert last["status"] == "COMPLETED"

    async def test_retry_resubmits_from_the_recorded_step(
        self, subscribe_gql, mock_migration_service, mock_task_runner,
    ):
        mock_migration_service.prepare_retry.return_value = TaskStatus.DELETING_SOURCE
        mock_task_runner.observe.side_effect = (
            lambda *a, **kw: _mock_progress_gen(*_events())
        )

        await subscribe_gql(MIGRATION_RETRY_SUBSCRIPTION, {"input": {"taskId": TASK_ID}})

        mock_migration_service.prepare_retry.assert_awaited_once_with(TASK_ID)
        mock_task_runner.submit.assert_awaited_once_with(
            TASK_ID,
            executor_key=MIGRATION_EXECUTOR_KEY,
            start_from=TaskStatus.DELETING_SOURCE,
        )
