import strawberry

from src.schema.types.fileBrowse_type import VideoMutationResult
from src.resolvers.mutation_resolver import MutationResolver

@strawberry.type
class Mutation:
    updateVideoMetadata: VideoMutationResult = strawberry.mutation(resolver=MutationResolver.resolve_update_video_metadata)

    recordVideoView: VideoMutationResult = strawberry.mutation(resolver=MutationResolver.resolve_record_video_view)

    deleteVideo: VideoMutationResult = strawberry.mutation(resolver=MutationResolver.resolve_delete_video)
