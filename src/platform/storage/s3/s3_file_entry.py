from src.platform.storage.base_file_entry import BaseFileEntry, FileStat


class S3FileEntry(BaseFileEntry):
    """File entry representing an S3 object or a pseudo-directory (common prefix)."""

    def __init__(self, key: str, size: float = 0, mtime: float = 0, is_directory: bool = False):
        self._key = key
        self._size = size
        self._mtime = mtime
        self._is_directory = is_directory

    @property
    def path(self) -> str:
        return self._key

    @property
    def name(self) -> str:
        stripped = self._key.rstrip("/")
        return stripped.rsplit("/", 1)[-1]

    def is_file(self) -> bool:
        return not self._is_directory

    def is_dir(self) -> bool:
        return self._is_directory

    def stat(self) -> FileStat:
        return FileStat(size=self._size, mtime=self._mtime)
