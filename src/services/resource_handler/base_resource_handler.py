from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Iterator

from src.services.resource_handler.base_file_entry import BaseFileEntry


class BaseResourceHandler(ABC):
    """Abstract base class for resource IO operations and path conversion."""

    # --- IO operations ---

    @abstractmethod
    @contextmanager
    def list_directory(self, path: str) -> Iterator[Iterator[BaseFileEntry]]:
        """List entries in a directory. Returns a context manager yielding BaseFileEntry iterator."""
        ...

    @abstractmethod
    def get_entry(self, path: str) -> BaseFileEntry:
        """Get a single file/directory entry by its path (not via directory listing)."""
        ...

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def delete_file(self, path: str) -> None:
        ...

    # --- Path conversion ---

    @abstractmethod
    def convert_to_DB_format_path(self, path: str) -> str:
        """Convert a filesystem-access path to the DB storage format."""
        ...

    @abstractmethod
    def convert_to_FS_format_path(self, path: str) -> str:
        """Convert a DB storage path to the filesystem-access format."""
        ...

    @abstractmethod
    def get_path_standard_format(self, path: str) -> str:
        """Normalize path to standard format (forward slashes)."""
        ...

    # --- File utilities ---

    @abstractmethod
    def is_video_file(self, filename: str) -> bool:
        """Check if a file is a video based on its extension."""
        ...

    @abstractmethod
    def get_filename_without_extension(self, filename: str) -> str:
        """Get file name without extension."""
        ...
