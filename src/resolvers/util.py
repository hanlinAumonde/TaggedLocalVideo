from contextlib import contextmanager
import os
from src.errors import FileBrowseError
    
def is_video_file(filename: str, video_extensions: list[str]) -> bool:
    # Helper function to check if a file is a video based on its extension.
    _, ext = os.path.splitext(filename.lower())
    return ext in video_extensions

@contextmanager
def current_directory_context(abs_path: str, resource_paths: dict):
    if abs_path is None:
        yield resource_paths.items()
    else:
        # Browsing a specific directory
        with os.scandir(abs_path) as entries:
            yield entries

def get_path_standard_format(path: str) -> str:
        """Standardize path format"""
        return os.path.normpath(path).replace("\\", "/")

#@cached(TTLCache(maxsize=128, ttl=300))
def get_total_size_and_last_modified_time(directory_path: str, video_extensions: list[str]) -> tuple[float, float]:
    total_size = 0.0
    last_modified_time = 0.0

    try:
        with os.scandir(directory_path) as entries:
            for entry in entries:
                if entry.is_dir():
                    dir_size, dir_mtime = get_total_size_and_last_modified_time(
                        get_path_standard_format(entry.path),
                        video_extensions
                    )
                    total_size += dir_size
                    last_modified_time = max(last_modified_time, dir_mtime)
                elif entry.is_file() and is_video_file(entry.name, video_extensions):
                    try:
                        stat = entry.stat()
                        total_size += stat.st_size
                        last_modified_time = max(last_modified_time, stat.st_mtime)
                    except OSError as e:
                        raise FileBrowseError(f"Error accessing file {entry.path}: {str(e)}")
    except OSError as e:
        raise FileBrowseError(f"Error accessing directory {directory_path}: {str(e)}")
    
    # If no videos found, use the folder's modification time
    if last_modified_time == 0.0:
        try:
            stat = os.stat(directory_path)
            last_modified_time = stat.st_mtime
        except OSError as e:
            raise FileBrowseError(f"Error accessing directory {directory_path}: {str(e)}")
        
    return total_size, last_modified_time
    
    # TODO: This function is cached to improve performance when the same directory is accessed multiple times.

    # Explanation: 
    # In the frontend, user can refresh the directory to get updated info of a directory if he wants.
    # Because the total size and last modified time are just indexes to help users know more about the directory
    # Sometimes they not need the most up-to-date info, sometimes they wants to sort all directories and files quickly,
    # it's not necessary to keep them always up-to-date.

    # Idea: use a third-part lib to actively manage the timing of cache invalidation.