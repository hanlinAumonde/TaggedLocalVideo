"""Tests for migration progress and retry subscriptions."""

import pytest
from unittest.mock import AsyncMock

from src.services.tasks.state_machine import MigrationProgressStatus
from tests.graphql.helpers import (
    MIGRATION_PROGRESS_SUBSCRIPTION,
    MIGRATION_RETRY_SUBSCRIPTION,
    assert_no_errors,
    assert_error_contains,
)

pytestmark = pytest.mark.subscription


async def _mock_progress_gen(*events):
    for e in events:
        yield e


class TestMigrationProgressSubscription:
    async def test_migration_progress_streams_events(
        self, subscribe_gql, mock_migration_service,
    ):
        events = [
            MigrationProgressStatus(
                task_id="tid", status="PROCESSING",
                bytes_transferred=50, total_bytes=100,
                progress_percentage=50.0, message="Copying",
            ),
            MigrationProgressStatus(
                task_id="tid", status="COMPLETED",
                bytes_transferred=100, total_bytes=100,
                progress_percentage=100.0, message="Done",
            ),
        ]
        mock_migration_service.execute_migration.side_effect = (
            lambda *a, **kw: _mock_progress_gen(*events)
        )

        results = await subscribe_gql(MIGRATION_PROGRESS_SUBSCRIPTION, {
            "input": {"taskId": "507f1f77bcf86cd799439011"}
        })
        assert len(results) == 2
        assert_no_errors(results[0])
        assert_no_errors(results[1])

        first = results[0].data["migrationProgressSubscription"]
        assert first["bytesTransferred"] == 50
        assert first["progressPercentage"] == 50.0

        last = results[1].data["migrationProgressSubscription"]
        assert last["status"] == "COMPLETED"
        assert last["progressPercentage"] == 100.0


class TestMigrationRetrySubscription:
    async def test_migration_retry_streams_events(
        self, subscribe_gql, mock_migration_service,
    ):
        events = [
            MigrationProgressStatus(
                task_id="tid", status="PROCESSING",
                bytes_transferred=0, total_bytes=100,
                progress_percentage=0.0, message="Retrying",
            ),
            MigrationProgressStatus(
                task_id="tid", status="COMPLETED",
                bytes_transferred=100, total_bytes=100,
                progress_percentage=100.0, message="Retry completed",
            ),
        ]
        mock_migration_service.retry_task.side_effect = (
            lambda *a, **kw: _mock_progress_gen(*events)
        )

        results = await subscribe_gql(MIGRATION_RETRY_SUBSCRIPTION, {
            "input": {"taskId": "507f1f77bcf86cd799439011"}
        })
        assert len(results) == 2
        assert_no_errors(results[0])

        last = results[1].data["migrationRetrySubscription"]
        assert last["status"] == "COMPLETED"
