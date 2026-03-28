import os
from pathlib import Path

from src.services.resource_handler.base_file_entry import BaseFileEntry, FileStat


class LocalFSFileEntry(BaseFileEntry):
    """
    Local filesystem file entry. Can be constructed from:
    - os.DirEntry (from os.scandir, lightweight with cached stat)
    - str path (uses pathlib.Path for stat/type queries)
    """

    def __init__(self, *, dir_entry: os.DirEntry[str] | None = None, file_path: str | None = None):
        if dir_entry is not None:
            self._dir_entry = dir_entry
            self._pathlib_path = None
        elif file_path is not None:
            self._dir_entry = None
            self._pathlib_path = Path(file_path)
        else:
            raise ValueError("Either dir_entry or file_path must be provided")

    @property
    def path(self) -> str:
        if self._dir_entry is not None:
            return self._dir_entry.path
        return str(self._pathlib_path)

    @property
    def name(self) -> str:
        if self._dir_entry is not None:
            return self._dir_entry.name
        return self._pathlib_path.name

    def is_file(self) -> bool:
        if self._dir_entry is not None:
            return self._dir_entry.is_file()
        return self._pathlib_path.is_file()

    def is_dir(self) -> bool:
        if self._dir_entry is not None:
            return self._dir_entry.is_dir()
        return self._pathlib_path.is_dir()

    def stat(self) -> FileStat:
        if self._dir_entry is not None:
            s = self._dir_entry.stat()
        else:
            s = self._pathlib_path.stat()
        return FileStat(size=s.st_size, mtime=s.st_mtime)
