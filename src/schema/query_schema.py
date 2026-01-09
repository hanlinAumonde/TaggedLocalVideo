import strawberry
from src.schema.types.fileBrowse_type import FileBrowseNode, RelativePathInput
from src.schema.types.search_type import SuggestionInput, VideoSearchInput, VideoSearchResult
from src.schema.types.video_type import Video, VideoTag
from src.resolvers.query_resolver import QueryResolver

@strawberry.type
class Query:
    SearchVideos: VideoSearchResult = strawberry.field(resolver=QueryResolver.resolve_search_videos)

    getTopTags: list[VideoTag] = strawberry.field(resolver=QueryResolver.resolve_get_top_tags)

    getSuggestions: list[str] = strawberry.field(QueryResolver.resolve_get_suggestions)

    getVideoById: Video = strawberry.field(QueryResolver.resolve_get_video_by_id)

    browseDirectory: list[FileBrowseNode] = strawberry.field(QueryResolver.resolve_browse_directory)