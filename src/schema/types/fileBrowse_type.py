from typing import Optional
import strawberry

from src.schema.types.pydantic_types.fileBrowe_type import RelativePathInputModel
from src.schema.types.video_type import Video


@strawberry.type
class FileBrowseNode:
    node: Video

@strawberry.experimental.pydantic.input(model=RelativePathInputModel)
class RelativePathInput:
    # refreshFlag: bool = False  # If True, bypass any caching and get the latest info from disk
    # relativePath: strawberry.auto
    parsedPath: strawberry.auto

@strawberry.input
class VideoTagsMappingInput:
    videoId: strawberry.ID
    tags: list[str]

@strawberry.input
class TagsOperationBatchInput:
    append: bool # True for append, False for remove
    mappings: list[VideoTagsMappingInput] # videoId to list of tags

@strawberry.type
class TagsOperationBatchResult:
    success: bool
    successfulUpdatesMappings: list[strawberry.ID] 

@strawberry.type
class VideoMutationResult:
    success: bool
    video: Optional[Video] = None