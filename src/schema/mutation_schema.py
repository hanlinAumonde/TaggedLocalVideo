import strawberry
from src.resolvers.mutation_resolver import get_mutation_resolver
from src.schema.types.fileBrowse_type import VideoMutationResult

MutationResolver = get_mutation_resolver()

@strawberry.type
class Mutation:
    updateVideoMetadata: VideoMutationResult = strawberry.mutation(MutationResolver.resolve_update_video_metadata)

    recordVideoView: VideoMutationResult = strawberry.mutation(MutationResolver.resolve_record_video_view)

    deleteVideo: VideoMutationResult = strawberry.mutation(MutationResolver.resolve_delete_video)