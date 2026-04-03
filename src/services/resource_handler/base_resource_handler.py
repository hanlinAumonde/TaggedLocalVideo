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
    def get_size(self, path: str) -> float:
        """Get the size of a file at the given path."""
        ...

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if a file exists at the given path."""
        ...

    @abstractmethod
    def delete_file(self, path: str) -> None:
        """Delete the file at the given path."""
        ...

    # --- File content read/write ---

    @abstractmethod
    async def read_file_chunk(self, path: str, offset: int, length: int) -> bytes:
        """
        Read a chunk of file data from [offset, offset+length).

        :param path: FS-format path (filesystem path for LocalFS, object key for S3)
        :param offset: Starting byte offset
        :param length: Number of bytes to read
        :return: The bytes read
        """
        ...

    @abstractmethod
    async def write_file(self, path: str, data: bytes) -> None:
        """
        Write a complete file (for small files like thumbnails).

        :param path: FS-format path
        :param data: File content bytes
        """
        ...

    # --- Path resolution ---

    @abstractmethod
    def resolve_path(self, category: str, pseudo_name: str | None, sub_path: str | None) -> str:
        """
        Resolve a parsed relative path (from GraphQL request) into the handler's
        internal absolute/logical path representation.

        :param category: Resource category (e.g. "Local-resource", "S3-resource")
        :param pseudo_name: Pseudo name within category, or None for category-level
        :param sub_path: Remaining sub-path after pseudo_name, or None
        :return: Resolved path in the handler's native format
        """
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

    # --- External tool access ---

    def get_ffmpeg_accessible_path(self, path: str) -> str | None:
        """
        Return a path/URL that ffmpeg can use as -i input.
        Local handlers return the filesystem path; S3 handlers return a pre-signed URL.
        Returns None if the handler cannot provide direct access (pipe stdin will be used as fallback).
        """
        return None

    # --- File utilities (static) ---

    @staticmethod
    @abstractmethod
    def is_video_file(filename: str) -> bool:
        """Check if a file is a video based on its extension."""
        ...

    @staticmethod
    @abstractmethod
    def get_file_extension(filename: str) -> str:
        """Get the file extension from a filename."""
        ...

    @staticmethod
    @abstractmethod
    def get_filename_without_extension(filename: str) -> str:
        """Get file name without extension."""
        ...

    @staticmethod
    @abstractmethod
    def join_path(*parts: str) -> str:
        """Join path parts using the handler's path separator."""
        ...

    @staticmethod
    @abstractmethod
    def dirname(path: str) -> str:
        """Get the parent directory of a path."""
        ...
