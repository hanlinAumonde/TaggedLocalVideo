import strawberry

from src.schema.types.fileBrowse_type import VideoMutationResult
from src.resolvers import mutation_resolver

@strawberry.type
class Mutation:
    updateVideoMetadata: VideoMutationResult = strawberry.mutation(resolver=mutation_resolver.resolve_update_video_metadata)

    recordVideoView: VideoMutationResult = strawberry.mutation(resolver=mutation_resolver.resolve_record_video_view)

    deleteVideo: VideoMutationResult = strawberry.mutation(resolver=mutation_resolver.resolve_delete_video)
