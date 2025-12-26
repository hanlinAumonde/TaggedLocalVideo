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
class SearchField(Enum):
    TITLE = "title"
    AUTHOR = "author"
    TAGS = "tags"

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

@strawberry.type
class SuggestionResults:
    results: list[str] | list[VideoTag]

@strawberry.input
class VideoSearchInput:
    titleKeyword: SerachKeyword
    author: SerachKeyword
    tags: list[str]
    sortBy: VideoSortOption = VideoSortOption.LATEST
    limit: Optional[int] = 5
    currentPageNumber: Optional[int] = 1

@strawberry.type
class VideoSearchResult:
    pagination: Pagination
    videos: list[Video]
