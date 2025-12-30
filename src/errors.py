class VideoNotFoundError(Exception):
    def __init__(self, video_id: str):
        self.video_id = video_id
        super().__init__(f"Video with ID {video_id} not found")


class InvalidPathError(Exception):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Invalid path: {path}")


class FileBrowseError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"File browse error: {message}")

class DatabaseOperationError(Exception):
    def __init__(self, operation: str, details: str):
        self.operation = operation
        self.details = details
        super().__init__(f"Database operation '{operation}' failed: {details}")
