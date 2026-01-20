from typing import Optional
import strawberry
from enum import Enum

from src.schema.types.video_type import Video, VideoTag
from src.schema.types.pydantic_types.search_type import (
    SearchKeywordModel,
    SuggestionInputModel,
    VideoSearchInputModel
)


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


@strawberry.experimental.pydantic.input(model=SearchKeywordModel)
class SerachKeyword:
    keyWord: strawberry.auto


@strawberry.experimental.pydantic.input(model=SuggestionInputModel)
class SuggestionInput:
    keyword: SerachKeyword
    suggestionType: SearchField


@strawberry.experimental.pydantic.input(model=VideoSearchInputModel)
class VideoSearchInput:
    titleKeyword: SerachKeyword
    author: SerachKeyword
    tags: strawberry.auto
    sortBy: VideoSortOption = VideoSortOption.LATEST
    fromPage: SearchFrom
    currentPageNumber: strawberry.auto


@strawberry.type
class VideoSearchResult:
    pagination: Pagination
    videos: list[Video]

