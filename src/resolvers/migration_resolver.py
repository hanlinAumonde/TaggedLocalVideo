from typing import AsyncGenerator

import pymongo
import strawberry

from src.context import ContextEnum, get_context_value
from src.db.models.MigrationTask_model import MigrationTaskModel, MigrationStatus
from src.errors import InputValidationError
from src.logger import get_logger
from src.schema.types.migration_type import (
    CreateMigrationTaskInput,
    MigrationPreflightInput,
    MigrationPreflightResult,
    MigrationProgressStatus,
    MigrationTask,
    MigrationTaskActionInput,
    MigrationTaskListResult,
    MigrationTaskMutationResult,
    MigrationTaskQueryInput,
)
from src.services.migration_service import MigrationService
from src.services.resource_handler.absolute_path import AbsolutePath

logger = get_logger("migration_resolver")


async def resolve_migration_preflight(
    input: MigrationPreflightInput, info: strawberry.Info
) -> MigrationPreflightResult:
    try:
        validated = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="MigrationPreflightInput", issue="Invalid input data")

    handler_service = get_context_value(info, ContextEnum.RESOURCE_HANDLER_SERVICE)
    settings = get_context_value(info, ContextEnum.SETTINGS)

    source_path = AbsolutePath.from_relative_path(
        parsedPath=validated.source_relative_path.parsedPath,
        handlerService=handler_service,
        settings=settings,
    )
    target_dir_path = AbsolutePath.from_relative_path(
        parsedPath=validated.target_dir_relative_path.parsedPath,
        handlerService=handler_service,
        settings=settings,
    )

    service: MigrationService = get_context_value(info, ContextEnum.MIGRATION_SERVICE)
    result = await service.preflight(source_path, target_dir_path)

    return MigrationPreflightResult(
        valid=result.valid,
        source_file_size=result.source_file_size,
        conflict_exists=result.conflict_exists,
        space_available=result.space_available,
        space_sufficient=result.space_sufficient,
        already_migrating=result.already_migrating,
        same_location=result.same_location,
        error_message=result.error_message,
    )


async def resolve_create_migration_task(
    input: CreateMigrationTaskInput, info: strawberry.Info
) -> MigrationTaskMutationResult:
    try:
        validated = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="CreateMigrationTaskInput", issue="Invalid input data")

    handler_service = get_context_value(info, ContextEnum.RESOURCE_HANDLER_SERVICE)
    settings = get_context_value(info, ContextEnum.SETTINGS)

    source_path = AbsolutePath.from_relative_path(
        parsedPath=validated.source_relative_path.parsedPath,
        handlerService=handler_service,
        settings=settings,
    )
    target_dir_path = AbsolutePath.from_relative_path(
        parsedPath=validated.target_dir_relative_path.parsedPath,
        handlerService=handler_service,
        settings=settings,
    )

    service: MigrationService = get_context_value(info, ContextEnum.MIGRATION_SERVICE)
    task = await service.create_task(source_path, target_dir_path, validated.conflict_strategy)
    return MigrationTaskMutationResult(
        success=True,
        task=MigrationTask.from_model(task),
    )


async def resolve_cancel_migration_task(
    input: MigrationTaskActionInput, info: strawberry.Info
) -> MigrationTaskMutationResult:
    try:
        validated = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="MigrationTaskActionInput", issue="Invalid input data")

    service: MigrationService = get_context_value(info, ContextEnum.MIGRATION_SERVICE)
    task = await service.cancel_task(validated.task_id)
    return MigrationTaskMutationResult(
        success=True,
        task=MigrationTask.from_model(task),
    )


async def resolve_migration_progress(
    input: MigrationTaskActionInput, info: strawberry.Info
) -> AsyncGenerator[MigrationProgressStatus, None]:
    try:
        validated = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="MigrationTaskActionInput", issue="Invalid input data")

    service: MigrationService = get_context_value(info, ContextEnum.MIGRATION_SERVICE)
    async for status in service.execute_migration(validated.task_id):
        yield MigrationProgressStatus.from_service(status)


async def resolve_migration_retry(
    input: MigrationTaskActionInput, info: strawberry.Info
) -> AsyncGenerator[MigrationProgressStatus, None]:
    try:
        validated = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="MigrationTaskActionInput", issue="Invalid input data")

    service: MigrationService = get_context_value(info, ContextEnum.MIGRATION_SERVICE)
    async for status in service.retry_task(validated.task_id):
        yield MigrationProgressStatus.from_service(status)


async def resolve_get_migration_tasks(
    input: MigrationTaskQueryInput, info: strawberry.Info
) -> MigrationTaskListResult:
    try:
        validated = input.to_pydantic()
    except Exception as e:
        logger.exception(f"Input validation error: {e}")
        raise InputValidationError(field="MigrationTaskQueryInput", issue="Invalid input data")

    query_filter: dict = {}
    if validated.status_filter:
        query_filter["status"] = {"$in": validated.status_filter}

    total_count = await MigrationTaskModel.find(query_filter).count()

    skip = (validated.page - 1) * validated.page_size
    task_models = (
        await MigrationTaskModel.find(query_filter)
        .sort([("created_at", pymongo.DESCENDING)])
        .skip(skip)
        .limit(validated.page_size)
        .to_list()
    )

    tasks = [MigrationTask.from_model(m) for m in task_models]
    return MigrationTaskListResult(
        tasks=tasks,
        total_count=total_count,
        page=validated.page,
        page_size=validated.page_size,
    )
