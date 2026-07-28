from enum import Enum
from typing import Optional
from beanie import Document
import pymongo
from pymongo import IndexModel


class MigrationStatus(str, Enum):
    # Normal flow
    PENDING = "PENDING"
    COPYING = "COPYING"
    COPY_DONE = "COPY_DONE"
    UPDATING_DB = "UPDATING_DB"
    DB_UPDATED = "DB_UPDATED"
    DELETING_SOURCE = "DELETING_SOURCE"
    COMPLETED = "COMPLETED"

    # Abnormal / interrupted
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MigrationTaskModel(Document):
    # Path info (DB format)
    source_path: str
    source_category: str
    target_path: str
    target_category: str
    file_name: str

    # File info
    file_size: int
    bytes_transferred: int = 0

    # Status
    status: str = MigrationStatus.PENDING
    error_message: Optional[str] = None
    failed_step: Optional[str] = None

    # Conflict resolution
    conflict_strategy: Optional[str] = None
    renamed_target_path: Optional[str] = None

    # Timestamps
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None

    class Settings:
        name = "migration_tasks"
        indexes = [
            [("status", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
            [("source_path", pymongo.ASCENDING)],
            [("target_path", pymongo.ASCENDING)],
            IndexModel(
                [("source_path", pymongo.ASCENDING)],
                unique=True,
                partialFilterExpression={
                    "status": {"$nin": ["COMPLETED", "FAILED", "CANCELLED"]}
                },
            ),
            IndexModel(
                [("target_path", pymongo.ASCENDING)],
                unique=True,
                partialFilterExpression={
                    "status": {"$nin": ["COMPLETED", "FAILED", "CANCELLED"]}
                },
            ),
        ]
