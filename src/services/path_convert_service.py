from functools import lru_cache
import os
from src.config import get_settings
from src.errors import FileBrowseError

class PathService:
    def __init__(self):
        self.settings = get_settings()

    def get_path_standard_format(self, path: str) -> str:
        """Standardize path format"""
        return os.path.normpath(path).replace("\\", "/")
    
    def get_file_extension(self, file_path: str) -> str:
        """Get file extension in lower case"""
        return os.path.splitext(file_path)[1].lower()
    
    def get_filename_without_extension(self, file_path: str) -> str:
        """Get file name without extension"""
        return os.path.splitext(os.path.basename(file_path))[0]
    
    def is_video_file(self, filename: str) -> bool:
        """Helper function to check if a file is a video based on its extension."""
        _, ext = os.path.splitext(filename.lower())
        return ext in get_settings().video_extensions
    
    def convert_to_FS_format_path(self, path: str) -> str:
        """Convert absolute path to mounted path in container if ROOT_PATH is set"""
        FS_format_path = path
        if self.settings.ROOT_PATH:
            for pseudo_name, resource_path in self.settings.resource_paths.items():
                if FS_format_path.startswith(resource_path):
                    relative_sub_path = FS_format_path[len(resource_path):]
                    return self.get_path_standard_format(os.path.join(
                        self.settings.ROOT_PATH, pseudo_name, relative_sub_path.lstrip("/")
                    ))
        return self.get_path_standard_format(FS_format_path)

    def convert_to_DB_format_path(self, path: str) -> str:
        """Convert mounted path in container to local absolute path if ROOT_PATH is set"""
        DB_format_path = path
        if self.settings.ROOT_PATH:
            for pseudo_name, resource_path in self.settings.resource_paths.items():
                mounted_ROOT_PATH = self.get_path_standard_format(os.path.join(
                    self.settings.ROOT_PATH, pseudo_name
                ))
                if DB_format_path.startswith(mounted_ROOT_PATH):
                    relative_sub_path = DB_format_path[len(mounted_ROOT_PATH):]
                    return self.get_path_standard_format(os.path.join(
                        resource_path, relative_sub_path.lstrip("/")
                    ))
        return self.get_path_standard_format(DB_format_path)

@lru_cache
def get_path_service() -> PathService:
    return PathService()

class AbsolutePath:
    settings = get_settings()
    pathHelper = get_path_service()

    def __init__(self, abs_path: str | None):
        self.abs_path = abs_path

    @classmethod
    def from_relative_path(cls, parsedPath: tuple[str, str | None] | None) -> 'AbsolutePath':
        return cls(cls._get_absolute_resource_path(parsedPath))
    
    @classmethod
    def from_existing_path(cls, path: str) -> 'AbsolutePath':
        return cls(path)        
    
    @staticmethod
    def _get_absolute_resource_path(parsedPath: tuple[str, str | None] | None) -> str:
        settings = AbsolutePath.settings

        if parsedPath is None:
            abs_path = None  # Browse root directories
        else:
            pseudo_root_dir_name, sub_path = parsedPath
            if pseudo_root_dir_name not in settings.resource_paths:
                raise FileBrowseError(f"Pseudo root dir name '{pseudo_root_dir_name}' not found in resource paths.")
            
            if settings.ROOT_PATH:
                # Use ROOT_PATH as base path when provided (run in container)
                abs_resource_path = os.path.join(settings.ROOT_PATH, pseudo_root_dir_name)
            else:
                # Use configured resource path directly (run locally)
                abs_resource_path = settings.resource_paths[pseudo_root_dir_name]
            
            if sub_path is None:
                abs_path = abs_resource_path
            else:
                abs_path = abs_resource_path + sub_path

        return abs_path

    def DB_format_path(self) -> str | None:
        if self.abs_path is None:
            return None
        return self.pathHelper.convert_to_DB_format_path(self.abs_path)

    def FS_format_path(self) -> str | None:
        if self.abs_path is None:
            return None
        return self.pathHelper.convert_to_FS_format_path(self.abs_path)

    def get_path(self) -> str | None:
        return self.pathHelper.get_path_standard_format(self.abs_path) if self.abs_path else None

    def update_path(self, new_abs_path: str) -> None:
        self.abs_path = new_abs_path
