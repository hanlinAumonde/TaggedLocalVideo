from pydantic import BaseModel, field_validator

from src.schema.types.pydantic_types.fileBrowe_type import RelativePathInputModel


class MigrationPreflightInputModel(BaseModel):
    source_relative_path: RelativePathInputModel
    target_dir_relative_path: RelativePathInputModel


class CreateMigrationTaskInputModel(BaseModel):
    source_relative_path: RelativePathInputModel
    target_dir_relative_path: RelativePathInputModel
    conflict_strategy: str | None = None

    @field_validator("conflict_strategy", mode="after")
    @classmethod
    def validate_strategy(cls, v: str | None) -> str | None:
        if v is not None and v not in ("overwrite", "rename", "skip"):
            raise ValueError("conflict_strategy must be 'overwrite', 'rename', 'skip', or null")
        return v


class MigrationTaskActionInputModel(BaseModel):
    task_id: str


class MigrationTaskQueryInputModel(BaseModel):
    status_filter: list[str] | None = None
    page: int = 1
    page_size: int = 20

    @field_validator("page", mode="after")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page must be >= 1")
        return v

    @field_validator("page_size", mode="after")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("page_size must be between 1 and 100")
        return v
