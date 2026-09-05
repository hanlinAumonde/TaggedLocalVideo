from enum import Enum

import strawberry

from src.schema.types.video_type import Video, VideoTag
from src.features.catalog.catalog_service import SearchField, VideoSortOption
from src.schema.types.pydantic_types.search_type import (
    SearchKeywordModel,
    SuggestionInputModel,
    VideoSearchInputModel
)

# Both belong to the catalogue service, which is what interprets them. Registered here
# rather than redeclared so the schema and the query logic cannot drift apart.
VideoSortOption = strawberry.enum(VideoSortOption)
SearchField = strawberry.enum(SearchField)


@strawberry.enum
class SearchFrom(Enum):
    """Which surface is asking. Decides page size, so it is purely a transport concern."""
    FrontalPage = "FrontalPage"
    SearchPage = "SearchPage"


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

@strawberry.type
class DirectoryMetadataResult:
    totalSize: float
    lastModifiedTime: float