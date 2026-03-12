from functools import lru_cache
import os
from src.config import get_settings
from src.errors import FileBrowseError
from src.schema.types.pydantic_types.fileBrowe_type import RelativePathInputModel

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
    
    def get_absolute_root_resource_path(self, pseudo_root_dir_name: str) -> str:
        """Get the absolute resource path from pseudo root dir name and sub path"""
        resource_paths = self.settings.resource_paths

        if pseudo_root_dir_name not in resource_paths:
            raise FileBrowseError(f"Pseudo root dir name '{pseudo_root_dir_name}' not found in resource paths.")

        if self.settings.ROOT_PATH:
            # Use ROOT_PATH as base path when provided (run in container)
            abs_path = os.path.join(self.settings.ROOT_PATH, pseudo_root_dir_name)
        else:
            # Use configured resource path directly (run locally)
            abs_path = resource_paths[pseudo_root_dir_name]

        return self.get_path_standard_format(abs_path)
    
    def get_absolute_resource_path(self, relativePathInputModel: RelativePathInputModel) -> str:
        if relativePathInputModel.parsedPath is None:
            abs_path = None  # Browse root directories
        else:
            pseudo_root_dir_name, sub_path = relativePathInputModel.parsedPath
            abs_resource_path = self.get_absolute_root_resource_path(pseudo_root_dir_name)
            
            if sub_path is None:
                abs_path = abs_resource_path
            else:
                abs_path = abs_resource_path + sub_path

        return abs_path

    def to_mounted_path(self, local_path: str) -> str:
        """Convert absolute path to mounted path in container if ROOT_PATH is set"""
        mounted_path = local_path
        if self.settings.ROOT_PATH:
            for pseudo_name, resource_path in self.settings.resource_paths.items():
                if mounted_path.startswith(resource_path):
                    relative_sub_path = mounted_path[len(resource_path):]
                    return self.get_path_standard_format(os.path.join(
                        self.settings.ROOT_PATH, pseudo_name, relative_sub_path.lstrip("/")
                    ))
        return self.get_path_standard_format(mounted_path)

    def to_host_path(self, mounted_path: str) -> str:
        """Convert mounted path in container to local absolute path if ROOT_PATH is set"""
        local_path = mounted_path
        if self.settings.ROOT_PATH:
            for pseudo_name, resource_path in self.settings.resource_paths.items():
                mounted_ROOT_PATH = self.get_path_standard_format(os.path.join(
                    self.settings.ROOT_PATH, pseudo_name
                ))
                if local_path.startswith(mounted_ROOT_PATH):
                    relative_sub_path = local_path[len(mounted_ROOT_PATH):]
                    return self.get_path_standard_format(os.path.join(
                        resource_path, relative_sub_path.lstrip("/")
                    ))
        return self.get_path_standard_format(local_path)

@lru_cache
def get_path_service() -> PathService:
    return PathService()