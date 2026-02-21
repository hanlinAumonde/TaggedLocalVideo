from typing import Optional
from beanie import Document, Indexed
import pymongo
from pydantic import BaseModel, Field

class VideoModel(Document):
    path: Indexed(str, pymongo.ASCENDING, unique=True)  # type: ignore 
    isDir: bool
    lastModifyTime: Indexed(float, pymongo.DESCENDING)  # type: ignore
    name: str
    size: float
    tags: list[str]  
    
    author: Optional[str] = "Unknown"
    introduction: Optional[str] = ""
    loved: Optional[bool] = False
    viewCount: Optional[int] = 0
    lastViewTime: Optional[float] = 0.0
    thumbnail: Optional[str] = None
    duration: Optional[float] = 0.0

    class Settings:
        name = "videos"
        indexes = [
            [("tags", pymongo.ASCENDING)],
            [("viewCount", pymongo.DESCENDING)],
            [("lastViewTime", pymongo.DESCENDING)],
            [("loved", pymongo.DESCENDING)],
            [("author", pymongo.ASCENDING)],
            # compound index: loved + lastViewTime (used for loved videos)
            [("loved", pymongo.DESCENDING), ("lastViewTime", pymongo.DESCENDING)],
            # compound index: viewCount + lastViewTime (used for popular videos)
            [("viewCount", pymongo.DESCENDING), ("lastViewTime", pymongo.DESCENDING)],
            [("duration", pymongo.DESCENDING)],
        ]

class VideoTagModel(Document):
    name: Indexed(str, pymongo.ASCENDING, unique=True)  # type: ignore 
    tag_count: int = Field(Indexed(int, pymongo.DESCENDING), alias="count")  # type: ignore

    class Settings:
        name = "tags"