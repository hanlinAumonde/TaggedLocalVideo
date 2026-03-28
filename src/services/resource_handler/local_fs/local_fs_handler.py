from contextlib import contextmanager
from typing import Iterator
import os

from src.config import get_settings
from src.services.resource_handler.base_resource_handler import BaseResourceHandler
from src.services.resource_handler.base_file_entry import BaseFileEntry
from src.services.resource_handler.local_fs.local_fs_file_entry import LocalFSFileEntry


class LocalFSResourceHandler(BaseResourceHandler):
    """Resource handler for local filesystem operations."""

    def __init__(self, category: str, pseudo_paths: dict[str, str], root_path: str | None):
        """
        :param category: Category name (e.g. "Local-resource")
        :param pseudo_paths: Mapping of pseudo_name -> host_path for this category
        :param root_path: ROOT_PATH env var (container mount base), None for local dev
        """
        self._category = category
        self._pseudo_paths = pseudo_paths
        self._root_path = root_path

    # --- IO operations ---

    @contextmanager
    def list_directory(self, path: str) -> Iterator[Iterator[BaseFileEntry]]:
        with os.scandir(path) as entries:
            yield (LocalFSFileEntry(dir_entry=entry) for entry in entries)

    def get_entry(self, path: str) -> BaseFileEntry:
        """Get a single entry by path using pathlib."""
        return LocalFSFileEntry(file_path=path)

    def file_exists(self, path: str) -> bool:
        return os.path.exists(path)

    def delete_file(self, path: str) -> None:
        os.remove(path)

    # --- Path conversion ---

    def convert_to_DB_format_path(self, path: str) -> str:
        """Convert mounted container path to absolute host path (DB storage format)."""
        db_path = path
        if self._root_path:
            for pseudo_name, host_path in self._pseudo_paths.items():
                mounted_root = self.get_path_standard_format(
                    os.path.join(self._root_path, self._category, pseudo_name)
                )
                if db_path.startswith(mounted_root):
                    relative_sub = db_path[len(mounted_root):]
                    return self.get_path_standard_format(
                        os.path.join(host_path, relative_sub.lstrip("/"))
                    )
        return self.get_path_standard_format(db_path)

    def convert_to_FS_format_path(self, path: str) -> str:
        """Convert absolute host path (DB format) to mounted container path (FS access format)."""
        fs_path = path
        if self._root_path:
            for pseudo_name, host_path in self._pseudo_paths.items():
                if fs_path.startswith(host_path):
                    relative_sub = fs_path[len(host_path):]
                    return self.get_path_standard_format(
                        os.path.join(self._root_path, self._category, pseudo_name, relative_sub.lstrip("/"))
                    )
        return self.get_path_standard_format(fs_path)

    def get_path_standard_format(self, path: str) -> str:
        return os.path.normpath(path).replace("\\", "/")

    # --- File utilities ---

    def is_video_file(self, filename: str) -> bool:
        _, ext = os.path.splitext(filename.lower())
        return ext in get_settings().video_extensions

    def get_filename_without_extension(self, filename: str) -> str:
        return os.path.splitext(os.path.basename(filename))[0]
