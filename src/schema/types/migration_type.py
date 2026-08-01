from enum import Enum
from typing import Optional

import strawberry

from src.db.models.MigrationTask_model import MigrationTaskModel
from src.schema.types.fileBrowse_type import RelativePathInput
from src.schema.types.pydantic_types.migration_type import (
    MigrationPreflightInputModel,
    CreateMigrationTaskInputModel,
    MigrationTaskActionInputModel,
    MigrationTaskQueryInputModel,
)


@strawberry.enum
class MigrationStatusEnum(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESS_DONE = "PROCESS_DONE"
    UPDATING_DB = "UPDATING_DB"
    DB_UPDATED = "DB_UPDATED"
    DELETING_SOURCE = "DELETING_SOURCE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@strawberry.type
class MigrationPreflightResult:
    valid: bool
    source_file_size: int
    conflict_exists: bool
    space_available: int | None
    space_sufficient: bool | None
    already_migrating: bool
    same_location: bool
    error_message: str | None = None


@strawberry.type
class MigrationTask:
    id: strawberry.ID
    source_path: str
    source_category: str
    target_path: str
    target_category: str
    file_name: str
    file_size: int
    bytes_transferred: int
    status: MigrationStatusEnum
    error_message: str | None
    failed_step: str | None
    conflict_strategy: str | None
    renamed_target_path: str | None
    created_at: float
    updated_at: float
    completed_at: float | None

    @classmethod
    def from_model(cls, model: MigrationTaskModel) -> "MigrationTask":
        return cls(
            id=strawberry.ID(str(model.id)),
            source_path=model.source_path,
            source_category=model.source_category,
            target_path=model.target_path,
            target_category=model.target_category,
            file_name=model.file_name,
            file_size=model.file_size,
            bytes_transferred=model.bytes_transferred,
            status=MigrationStatusEnum(model.status),
            error_message=model.error_message,
            failed_step=model.failed_step,
            conflict_strategy=model.conflict_strategy,
            renamed_target_path=model.renamed_target_path,
            created_at=model.created_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at,
        )


@strawberry.type
class MigrationTaskListResult:
    tasks: list[MigrationTask]
    total_count: int
    page: int
    page_size: int


@strawberry.type
class MigrationProgressStatus:
    task_id: str
    status: MigrationStatusEnum
    bytes_transferred: int
    total_bytes: int
    progress_percentage: float
    message: str | None = None

    @classmethod
    def from_service(cls, svc_status) -> "MigrationProgressStatus":
        return cls(
            task_id=svc_status.task_id,
            status=MigrationStatusEnum(svc_status.status),
            bytes_transferred=svc_status.bytes_transferred,
            total_bytes=svc_status.total_bytes,
            progress_percentage=svc_status.progress_percentage,
            message=svc_status.message,
        )


@strawberry.type
class MigrationTaskMutationResult:
    success: bool
    task: Optional[MigrationTask] = None
    error_message: str | None = None


# --- Input types ---

@strawberry.experimental.pydantic.input(model=MigrationPreflightInputModel)
class MigrationPreflightInput:
    source_relative_path: RelativePathInput
    target_dir_relative_path: RelativePathInput


@strawberry.experimental.pydantic.input(model=CreateMigrationTaskInputModel)
class CreateMigrationTaskInput:
    source_relative_path: RelativePathInput
    target_dir_relative_path: RelativePathInput
    conflict_strategy: strawberry.auto


@strawberry.experimental.pydantic.input(model=MigrationTaskActionInputModel)
class MigrationTaskActionInput:
    task_id: strawberry.auto


@strawberry.experimental.pydantic.input(model=MigrationTaskQueryInputModel)
class MigrationTaskQueryInput:
    status_filter: strawberry.auto
    page: strawberry.auto
    page_size: strawberry.auto
