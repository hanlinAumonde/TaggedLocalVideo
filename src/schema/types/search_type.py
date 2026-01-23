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
    Latest = "Latest"
    MostViewed = "MostViewed"
    Loved = "Loved"


@strawberry.enum
class SearchFrom(Enum):
    FrontalPage = "FrontalPage"
    SearchPage = "SearchPage"


@strawberry.enum
class SearchField(Enum):
    Name = "Name"
    Author = "Author"
    Tag = "Tag"


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
    sortBy: VideoSortOption = VideoSortOption.Latest
    fromPage: SearchFrom
    currentPageNumber: strawberry.auto


@strawberry.type
class VideoSearchResult:
    pagination: Pagination
    videos: list[Video]

