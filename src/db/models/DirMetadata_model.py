from beanie import Document, Indexed, before_event, Insert, Replace
import pymongo
from src.config import get_settings

class DirMetadataModel(Document):
    category: str
    path: Indexed(str, pymongo.ASCENDING, unique=True)  # type: ignore
    total_size: float
    last_modified_time: float

    @before_event(Insert, Replace)
    def validate_category(self):
        valid = get_settings().get_valid_categories()
        if self.category not in valid:
            raise ValueError(f"Invalid category '{self.category}'. Must be one of {valid}")

    class Settings:
        name = "dir_metadata"
        indexes = [
            [("category", pymongo.ASCENDING)],
        ]
