import strawberry
from src.schema.types.fileBrowse_type import FileBrowseNode, RelativePathInput
from src.schema.types.search_type import SuggestionInput, SuggestionResults, VideoSearchInput, VideoSearchResult
from src.schema.types.video_type import Video, VideoTag
from src.resolvers.query_resolver import (
    resolve_search_videos,
    resolve_get_top_tags,
    resolve_get_suggestions,
    resolve_get_video_by_id,
    resolve_browse_directory
)

@strawberry.type
class Query:
    @strawberry.field
    async def SearchVideos(self, input: VideoSearchInput, info: strawberry.Info) -> VideoSearchResult:
        """Search for videos based on various criteria."""
        return await resolve_search_videos(input, info)

    @strawberry.field
    async def getTopTags(self, info: strawberry.Info) -> list[VideoTag]:
        """Retrieve the top video tags."""
        return await resolve_get_top_tags(info)

    @strawberry.field
    async def getSuggestions(self, input: SuggestionInput, info: strawberry.Info) -> SuggestionResults:
        """Get suggestions (titles, authors, tags) based on a keyword and suggestion type."""
        return await resolve_get_suggestions(input, info)

    @strawberry.field
    async def getVideoById(self, videoId: strawberry.ID) -> Video:
        """Retrieve a video by its ID."""
        return await resolve_get_video_by_id(videoId)

    @strawberry.field
    async def browseDirectory(self, path: RelativePathInput, info: strawberry.Info) -> list[FileBrowseNode]:
        """Browse videos in a directory specified by a relative path."""
        return await resolve_browse_directory(path, info)