from typing import Optional
import strawberry
from enum import Enum

from src.schema.types.video_type import Video, VideoTag

@strawberry.enum
class VideoSortOption(Enum):
    LATEST = "latest"
    MOST_VIEWED = "most_viewed"
    LOVED = "loved"

@strawberry.enum
class SearchFrom(Enum):
    FrontalPage = "frontal_page"
    SearchPage = "search_page"

@strawberry.enum
class SearchField(Enum):
    NAME = "name"
    AUTHOR = "author"
    TAG = "tag"

@strawberry.type
class Pagination:
    size: int
    totalCount: int
    currentPageNumber: int

@strawberry.input
class SerachKeyword:
    keyWord: Optional[str] = None

@strawberry.input
class SuggestionInput:
    keyword: SerachKeyword
    suggestionType: SearchField

@strawberry.input
class VideoSearchInput:
    titleKeyword: SerachKeyword
    author: SerachKeyword
    tags: list[str]
    sortBy: VideoSortOption = VideoSortOption.LATEST
    fromPage: SearchFrom
    currentPageNumber: Optional[int] = 1

@strawberry.type
class VideoSearchResult:
    pagination: Pagination
    videos: list[Video]

