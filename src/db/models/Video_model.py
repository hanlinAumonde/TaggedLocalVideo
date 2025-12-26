from typing import Optional
from beanie import Document, Indexed
import pymongo
from pydantic import Field

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

    class Settings:
        name = "videos"
        indexes = [
            # 标签多键索引
            [("tags", pymongo.ASCENDING)],
            # 观看次数降序索引
            [("viewCount", pymongo.DESCENDING)],
            # 最后观看时间降序索引
            [("lastViewTime", pymongo.DESCENDING)],
            # 收藏状态索引
            [("loved", pymongo.DESCENDING)],
            # 作者索引(用于作者搜索)
            [("author", pymongo.ASCENDING)],
            # 复合索引: loved + lastViewTime (用于收藏视频按观看时间排序)
            [("loved", pymongo.DESCENDING), ("lastViewTime", pymongo.DESCENDING)],
            # 复合索引: viewCount + lastModifyTime (用于热门视频)
            [("viewCount", pymongo.DESCENDING), ("lastModifyTime", pymongo.DESCENDING)],
        ]

class VideoTagModel(Document):
    name: Indexed(str, pymongo.ASCENDING, unique=True)  # type: ignore 
    tag_count: int = Field(Indexed(int, pymongo.DESCENDING), alias="count")  # type: ignore

    class Settings:
        name = "tags"