import strawberry

from src.schema.types.fileBrowse_type import TagsOperationBatchInput, TagsOperationBatchResult, VideoMutationResult
from src.schema.types.video_type import UpdateVideoMetadataInput, Video
from src.resolvers.mutation_resolver import (
    resolve_update_video_metadata,
    resolve_batch_update_video_tags,
    resolve_record_video_view,
    resolve_delete_video
)


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def updateVideoMetadata(self, input: UpdateVideoMetadataInput) -> VideoMutationResult:
        """Update the metadata of a video."""
        return await resolve_update_video_metadata(input)

    @strawberry.mutation
    async def batchUpdateVideoTags(self, input: TagsOperationBatchInput) -> TagsOperationBatchResult:
        """Batch update tags for multiple videos."""
        return await resolve_batch_update_video_tags(input)

    @strawberry.mutation
    async def recordVideoView(self, videoId: strawberry.ID) -> VideoMutationResult:
        """Record a view for a video."""
        return await resolve_record_video_view(videoId)

    @strawberry.mutation
    async def deleteVideo(self, videoId: strawberry.ID) -> VideoMutationResult:
        """Delete a video by its ID."""
        return await resolve_delete_video(videoId)