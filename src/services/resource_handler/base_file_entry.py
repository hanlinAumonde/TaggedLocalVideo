from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class FileStat:
    """Platform-independent file stat result."""
    size: float
    mtime: float


class BaseFileEntry(ABC):
    """Abstract base class representing a file/directory entry in a resource handler."""

    @property
    @abstractmethod
    def path(self) -> str:
        """Full path of this entry (FS-format for local, key for S3, etc.)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this entry (file/directory name only, no parent path)."""
        ...

    @abstractmethod
    def is_file(self) -> bool:
        """Return True if this entry is a file."""
        ...

    @abstractmethod
    def is_dir(self) -> bool:
        """Return True if this entry is a directory."""
        ...

    @abstractmethod
    def stat(self) -> FileStat:
        """Return the file statistics for this entry."""

        ...
